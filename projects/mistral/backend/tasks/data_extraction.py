# -*- coding: utf-8 -*-

import shlex
import subprocess
import os
import datetime
import tarfile
# import shutil
import glob
# from pathlib import Path
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.services.mail import send_mail
from restapi.utilities.templates import get_html_template
# from restapi.confs import UPLOAD_FOLDER
from celery import states
from celery.exceptions import Ignore
from mistral.services.arkimet import DATASET_ROOT, BeArkimet as arki
from mistral.services.dballe import BeDballe as dballe
from mistral.services.requests_manager import RequestManager
from mistral.exceptions import DiskQuotaException
from mistral.exceptions import PostProcessingException

# postprocessing
from mistral.tools import derived_variables as pp1
from mistral.tools import statistic_elaboration as pp2
from mistral.tools import grid_interpolation as pp3_1
from mistral.tools import grid_cropping as pp3_2
from mistral.tools import spare_point_interpol as pp3_3
from mistral.tools import output_formatting

from restapi.utilities.logs import log

celery_app = CeleryExt.celery_app

DOWNLOAD_DIR = '/data'


@celery_app.task(bind=True)
# @send_errors_by_email
def data_extract(self, user_id, datasets, reftime=None, filters=None, postprocessors=[], output_format=None,
                 request_id=None,
                 schedule_id=None):
    with celery_app.app.app_context():
        log.info("Start task [{}:{}]", self.request.id, self.name)
        extra_msg = ''
        try:
            db = celery_app.get_service('sqlalchemy')
            schedule = None
            if schedule_id is not None:
                # load schedule for this request
                schedule = db.Schedule.query.get(schedule_id)
                if schedule is None:
                    raise ReferenceError(
                        "Cannot find schedule reference for task {}".format(
                            self.request.id))
                # adapt the request reftime
                reftime = adapt_reftime(schedule, reftime)

                # create an entry in request db linked to the scheduled request entry
                product_name = RequestManager.get_schedule_name(db, schedule_id)
                request = RequestManager.create_request_record(db, user_id, product_name, {
                    'datasets': datasets,
                    'reftime': reftime,
                    'filters': filters,
                    'postprocessors': postprocessors,
                    'output_format': output_format,
                }, schedule_id=schedule_id)
                # update the entry with celery task id
                request.task_id = self.request.id
                request_id = request.id
                db.session.commit()
                log.debug('Schedule at: {}, Request <ID:{}>', schedule_id, request.id)
            else:
                # load request by id
                request = db.Request.query.get(request_id)
                if request is None:
                    raise ReferenceError("Cannot find request reference for task {}".format(self.request.id))

            # get the format of the datasets
            dataset_format = arki.get_datasets_format(datasets)

            # TODO and if are observation data in arkimet and not in dballe?
            # create a query for arkimet
            if dataset_format == 'grib':
                query = ''  # default to no matchers
                if filters is not None:
                    query = arki.parse_matchers(filters)
                    log.debug('Arkimet query: {}', query)
                if reftime is not None:
                    reftime_query = arki.parse_reftime(reftime['from'], reftime['to'])
                    query = ";".join([reftime_query, query]) if query != '' else reftime_query

            # create download user dir if it doesn't exist
            uuid = RequestManager.get_uuid(db, user_id)
            user_dir = os.path.join(DOWNLOAD_DIR, uuid)
            os.makedirs(user_dir, exist_ok=True)

            # check that the datasets are all under the same license
            license = arki.get_unique_license(datasets)
            log.debug('license: {}', license)
            # get license file
            license_file = os.path.join(os.curdir, 'mistral', 'licenses', '{}.txt'.format(license))
            if not os.path.isfile(license_file):
                raise IOError('License file not found')

            # output filename in the user space
            # max filename len = 64
            out_filename = 'data-{utc_now}-{id}.{fileformat}'.format(
                utc_now=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ"),
                id=self.request.id,
                fileformat=dataset_format)
            # final result
            outfile = os.path.join(user_dir, out_filename)

            if dataset_format == 'grib':
                if schedule:
                    esti_data_size = check_user_quota(user_id, user_dir, datasets, query, db, schedule_id)
                else:
                    esti_data_size = check_user_quota(user_id, user_dir, datasets, query, db)
                '''
                $ arki-query [OPZIONI] QUERY DATASET...
                '''
                ds = ' '.join([DATASET_ROOT + '{}'.format(i) for i in datasets])
                arki_query_cmd = shlex.split("arki-query --data '{}' {}".format(query, ds))
                log.debug(arki_query_cmd)

            # observed data. in future the if statement will be for data using arkimet and data using dballe
            else:
                # TODO how can i check user quota using dballe??
                log.debug('observation in dballe')

            if postprocessors:
                log.debug(postprocessors)
                # check if requested postprocessors are enabled
                for p in postprocessors:
                    pp_type = p.get('type')
                    enabled_postprocessors = (
                        'derived_variables', 'grid_interpolation', 'grid_cropping', 'spare_point_interpolation',
                        'statistic_elaboration')
                    if pp_type not in enabled_postprocessors:
                        raise ValueError("Unknown post-processor: {}", pp_type)

                    log.debug(
                        'Data extraction with post-processing <{}>', pp_type)

                # temporarily save the data extraction output
                tmp_outfile = os.path.join(user_dir, out_filename + '.tmp')
                # call data extraction
                if dataset_format == 'grib':
                    arkimet_extraction(arki_query_cmd, tmp_outfile)
                else:
                    # dballe_extraction(datasets, filters, reftime, outfile)
                    observed_extraction(datasets, filters, reftime, tmp_outfile)

                # case of single postprocessor
                if len(postprocessors) == 1:
                    try:
                        p = postprocessors[0]
                        pp_type = p.get('type')

                        if pp_type == 'derived_variables':
                            pp1_output = pp1.pp_derived_variables(datasets=datasets, params=p,
                                                                  tmp_extraction=tmp_outfile, user_dir=user_dir,
                                                                  fileformat=dataset_format)
                            # join pp1_output and tmp_extraction in output file
                            cat_cmd = ['cat', tmp_outfile, pp1_output]
                            with open(outfile, mode='w') as out:
                                ext_proc = subprocess.Popen(cat_cmd, stdout=out)
                                ext_proc.wait()
                                if ext_proc.wait() != 0:
                                    raise Exception('Failure in data extraction')

                        elif pp_type == 'statistic_elaboration':
                            params = []
                            params.append(p)
                            pp2.pp_statistic_elaboration(params=params, input=tmp_outfile, output=outfile,
                                                         fileformat=dataset_format)

                        elif pp_type == 'grid_interpolation':
                            pp3_1.pp_grid_interpolation(params=p, input=tmp_outfile, output=outfile)

                        elif pp_type == 'grid_cropping':
                            pp3_2.pp_grid_cropping(params=p, input=tmp_outfile, output=outfile)

                        elif pp_type == 'spare_point_interpolation':
                            # change output extension from .grib to .BUFR
                            outfile_name, outfile_ext = os.path.splitext(out_filename)
                            out_filename = outfile_name + '.BUFR'
                            outfile = os.path.join(user_dir, out_filename)
                            # bufr_outfile = outfile_name+'.BUFR'
                            # pp3_3.pp_sp_interpolation(params=p, input=tmp_outfile, output=bufr_outfile,fileformat=dataset_format)
                            pp3_3.pp_sp_interpolation(params=p, input=tmp_outfile, output=outfile,
                                                      fileformat=dataset_format)

                    finally:
                        # always remove tmp file
                        tmp_filelist = glob.glob(os.path.join(user_dir, "*.tmp"))
                        for f in tmp_filelist:
                            os.remove(f)
                        # if pp_type == 'spare_point_interpolation':
                        #     # remove the temporary folder where the files for the interpolation were uploaded
                        #     uploaded_filepath = Path(p.get('coord-filepath'))
                        #     shutil.rmtree(uploaded_filepath.parent)

                # case of multiple postprocessor
                else:
                    # check if there is only one geographical postprocessor
                    pp_list = []
                    for p in postprocessors:
                        pp_list.append(p['type'])
                    pp3_list = ['grid_cropping', 'grid_interpolation', 'spare_point_interpolation']
                    if len(set(pp_list).intersection(set(pp3_list))) > 1:
                        raise PostProcessingException('Only one geographical postprocessing at a time can be executed')
                    try:

                        tmp_extraction_basename = os.path.basename(tmp_outfile)
                        pp_output = None
                        if any(d['type'] == 'derived_variables' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'derived_variables')
                            pp1_output = pp1.pp_derived_variables(datasets=datasets, params=p,
                                                                  tmp_extraction=tmp_outfile,
                                                                  user_dir=user_dir, fileformat=dataset_format)
                            # join pp1_output and tmp_extraction in output file
                            cat_cmd = ['cat', tmp_outfile, pp1_output]
                            # new temp file as pp output
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[
                                                              0] + '-pp1.{fileformat}.tmp'.format(
                                fileformat=dataset_format)
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            with open(pp_output, mode='w') as pp1_outfile:
                                ext_proc = subprocess.Popen(cat_cmd, stdout=pp1_outfile)
                                ext_proc.wait()
                                if ext_proc.wait() != 0:
                                    raise Exception('Failure in data extraction')
                        if any(d['type'] == 'statistic_elaboration' for d in postprocessors):
                            p = []
                            for item in postprocessors:
                                if item["type"] == 'statistic_elaboration':
                                    p.append(item)
                            # check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[
                                                              0] + '-pp2.{fileformat}.tmp'.format(
                                fileformat=dataset_format)
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp2.pp_statistic_elaboration(params=p, input=pp_input, output=pp_output,
                                                         fileformat=dataset_format)
                        if any(d['type'] == 'grid_cropping' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'grid_cropping')
                            # check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[
                                                              0] + '-pp3_2.{fileformat}.tmp'.format(
                                fileformat=dataset_format)
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp3_2.pp_grid_cropping(params=p, input=pp_input, output=pp_output)
                        if any(d['type'] == 'grid_interpolation' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'grid_interpolation')
                            # check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[
                                                              0] + '-pp3_1.{fileformat}.tmp'.format(
                                fileformat=dataset_format)
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp3_1.pp_grid_interpolation(params=p, input=pp_input, output=pp_output)
                        if any(d['type'] == 'spare_point_interpolation' for d in postprocessors):
                            p = next(item for item in postprocessors if item["type"] == 'spare_point_interpolation')
                            # check if the input has to be the previous postprocess output
                            pp_input = ''
                            if pp_output is not None:
                                pp_input = pp_output
                            else:
                                pp_input = tmp_outfile
                            # new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '-pp3_3.grib.tmp'
                            new_tmp_extraction_filename = tmp_extraction_basename.split('.')[0] + '.bufr'
                            out_filename = new_tmp_extraction_filename
                            pp_output = os.path.join(user_dir, new_tmp_extraction_filename)
                            pp3_3.pp_sp_interpolation(params=p, input=pp_input, output=pp_output,
                                                      fileformat=dataset_format)
                        # rename the final output of postprocessors as outfile unless it is not a bufr file
                        if pp_output.split('.')[-1] != 'bufr':
                            log.debug('dest: {}'.format(str(outfile)))
                            os.rename(pp_output, outfile)
                        # else:
                        #     # if it is a bufr file, the filename resulting from the pp is will be the new outifle filename
                        #     outfile = pp_output
                    finally:
                        log.debug('end of multiple postprocessors')
                    #     # remove all tmp file
                    #     tmp_filelist = glob.glob(os.path.join(user_dir, "*.tmp"))
                    #     for f in tmp_filelist:
                    #         os.remove(f)
                    # if there is, remove the temporary folder where the files for the sp_interpolation were uploaded
                    # if os.path.isdir(os.path.join(UPLOAD_FOLDER,uuid)):
                    #     shutil.rmtree(os.path.join(UPLOAD_FOLDER,uuid))
            else:
                if dataset_format == 'grib':
                    arkimet_extraction(arki_query_cmd, outfile)
                else:
                    # dballe_extraction(datasets, filters, reftime, outfile)
                    observed_extraction(datasets, filters, reftime, outfile)

            if output_format:
                filebase, fileext = os.path.splitext(out_filename)
                input = os.path.join(user_dir, out_filename)
                output = os.path.join(user_dir, filebase + "." + output_format)
                out_filepath = output_formatting.pp_output_formatting(output_format, input, output)
                out_filename = os.path.basename(out_filepath)
                # rename outfile correctly
                outfile = os.path.join(user_dir, out_filename)


            # get the actual data size
            data_size = os.path.getsize(os.path.join(user_dir, out_filename))
            log.debug('Actual resulting data size: {}'.format(data_size))
            if dataset_format == 'grib':
                if data_size > esti_data_size:
                    log.warning(
                        'Actual resulting data exceeds estimation of {}',
                        human_size(data_size - esti_data_size)
                    )

            # package data and license
            tar_filename = 'data-{utc_now}.tar.gz'.format(
                utc_now=datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ.%f"),
                id=self.request.id)
            tar_file = os.path.join(user_dir, tar_filename)
            with tarfile.open(tar_file, "w:gz") as tar:
                log.debug('--TAR ARCHIVE-------------------------')
                log.debug('data file: {}', outfile)
                tar.add(outfile, arcname=os.path.basename(outfile))
                log.debug('license file: {}', license_file)
                tar.add(license_file, arcname='LICENSE')
                log.debug('--------------------------------------')

            # delete out_filename
            os.remove(outfile)

            # create fileoutput record in db
            RequestManager.create_fileoutput_record(db, user_id, request_id, tar_filename, data_size)
            # update request status
            request.status = states.SUCCESS
            log.debug('reftime: {}', reftime)

        except DiskQuotaException as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(exc)
            # manually update the task state
            self.update_state(
                state=states.FAILURE,
                meta=message
            )
            raise Ignore()
        except PostProcessingException as exc:
            request.status = states.FAILURE
            request.error_message = str(exc)
            log.warning(exc)
            # manually update the task state
            self.update_state(
                state=states.FAILURE,
                meta=str(exc)
            )
            raise Ignore()
        except Exception as exc:
            # handle all the other exceptions
            request.status = states.FAILURE
            request.error_message = 'Failed to extract data'
            log.exception('Failed to extract data: {}', repr(exc))
            raise exc
        finally:
            # remove tmp file
            tmp_filelist = glob.glob(os.path.join(user_dir, "*.tmp"))
            for f in tmp_filelist:
                os.remove(f)

            request.end_date = datetime.datetime.utcnow()
            db.session.commit()
            log.info('Terminate task {} with state {}', self.request.id, request.status)
            # user notification via email
            user_email = db.session.query(db.User.email).filter_by(id=user_id).scalar()
            body_msg = request.error_message if request.error_message is not None else "Your data is ready for " \
                                                                                       "downloading"
            body_msg += extra_msg
            send_result_notication(user_email, request.name, request.status, body_msg)


def check_user_quota(user_id, user_dir, datasets, query, db, schedule_id=None):
    # check the output size
    esti_data_size = arki.estimate_data_size(datasets, query)
    log.debug('Resulting output size: {} ({})', esti_data_size, human_size(esti_data_size))
    # check for current used space
    used_quota = int(subprocess.check_output(['du', '-sb', user_dir]).split()[0])
    log.info('Current used space: {} ({})', used_quota, human_size(used_quota))

    # check for exceeding quota
    max_user_quota = db.session.query(db.User.disk_quota).filter_by(id=user_id).scalar()
    log.debug('MAX USER QUOTA for user<{}>: {}', user_id, max_user_quota)
    if used_quota + esti_data_size > max_user_quota:
        free_space = max(max_user_quota - used_quota, 0)
        # save error message in db
        message = 'Disk quota exceeded: required size {}; remaining space {}'.format(
            human_size(esti_data_size), human_size(free_space))
        # check if this request comes from a schedule. If so deactivate the schedule.
        if schedule_id is not None:
            # load schedule for this request
            schedule = db.Schedule.query.get(schedule_id)
            log.debug('Deactivate periodic task for schedule {}', schedule_id)
            if schedule.on_data_ready is False:
                if not CeleryExt.delete_periodic_task(name=str(schedule_id)):
                    raise Exception('Cannot delete periodic task for schedule {}'.format(schedule_id))
            RequestManager.update_schedule_status(db, schedule_id, False)
            extra_msg = '<br/><br/>Schedule "{}" temporary disabled for limit quota exceeded.'.format(schedule.name)
        raise DiskQuotaException(message)
    return esti_data_size


def arkimet_extraction(arki_query_cmd, outfile):
    with open(outfile, mode='w') as outfile:
        ext_proc = subprocess.Popen(arki_query_cmd, stdout=outfile)
        ext_proc.wait()
        if ext_proc.wait() != 0:
            raise Exception('Failure in data extraction')


def dballe_extraction(datasets, filters, reftime, outfile=None, ark_query=None, memdb=None, mixed=False):
    # get networks by dataset
    networks = []
    for ds in datasets:
        ds_networks = arki.get_observed_dataset_params(ds)
        for n in ds_networks:
            networks.append(n)
    # create a query for dballe
    if filters is not None:
        fields, queries = dballe.from_filters_to_lists(filters)
        if 'rep_memo' not in filters:
            fields.append('rep_memo')
            queries.append(networks)
    else:
        # if there aren't filters, data are filtered only by dataset's networks
        fields = ['rep_memo']
        queries = []
        queries.append(networks)
    if reftime is not None:
        fields.append('datetimemin')
        queries.append([reftime['from']])
        fields.append('datetimemax')
        queries.append([reftime['to']])

    log.debug('fields: {}, queries: {}', fields, queries)
    # if is a mixed request
    if mixed:
        # fill the db with the data from arkimet
        temp_db = dballe.fill_db_from_arkimet(datasets, ark_query)
        # fill the db with the data from dballe
        filled_db = dballe.extract_data(fields, queries, temp_db=temp_db)
        return filled_db
        # extract the data from the temporary db
    # if is the request of extraction from a temporary db
    elif memdb:
        dballe.extract_data(fields, queries, temp_db=memdb, outfile=outfile)
        # remember to clean the temporary db
        memdb.remove_all()
    else:
        # extract data only from dballe
        dballe.extract_data(fields, queries, outfile=outfile)


def observed_extraction(datasets, filters, reftime, outfile):
    # get db type
    date_min = None
    date_max = None
    if reftime is not None:
        date_min, date_max = dballe.parse_data_extraction_reftime(reftime['from'], reftime['to'])
        db_type = dballe.get_db_type(date_min, date_max)
        # replace the reftime with the parsed one
        reftime['from'] = date_min
        reftime['to'] = date_max
    else:
        db_type = 'mixed'
        refmin_arki = None
        refmax_arki = None

    if db_type == 'arkimet' or db_type == 'mixed':
        # get the datemax and datemin for arkimet query. if db_type is mixed, call the method to split the reftime
        partial_reftime = None
        if reftime is not None:
            if db_type == 'mixed':
                refmax_dballe, refmin_dballe, refmax_arki, refmin_arki = dballe.split_reftimes(date_min, date_max)
                # create a dictionary with the new reftime for dballe
                partial_reftime = {'from': refmin_dballe, 'to': refmax_dballe}
            else:
                refmin_arki = date_min
                refmax_arki = date_max
        # get the network filters
        network = []
        dataset_nets = []
        for ds in datasets:
            nets = arki.get_observed_dataset_params(ds)
            for n in nets:
                dataset_nets.append(n)
        if "network" in filters:
            for n in filters["network"]:
                network.append(n['dballe_p'])
            # check if the requested networks is compatible with the requested datasets
            log.debug('dataset nets: {}, network {}', dataset_nets, network)
            if not all(elem in dataset_nets for elem in network):
                raise Exception('Failure in data extraction: Invalid set of filters')
        else:
            # if there is not network specified in filters, extract all dataset networks
            network = None
        # build the arkimet query
        arkimet_query = dballe.build_arkimet_query(datemin=refmin_arki, datemax=refmax_arki, network=network)

        log.debug('type of extraction: {}', db_type)
        if db_type == 'arkimet':
            # extract data, fill the temporary db and get the temporary db in return
            temp_db = dballe.fill_db_from_arkimet(datasets, arkimet_query)

        if db_type == 'mixed':
            # extract data, fill the temporary db and get the temporary db in return
            temp_db = dballe_extraction(datasets, filters, partial_reftime, ark_query=arkimet_query, mixed=True)

        # extract the data from the temporary db
        dballe_extraction(datasets, filters, reftime, outfile=outfile, memdb=temp_db)

    else:
        # extract data from the general db
        dballe_extraction(datasets, filters, reftime, outfile=outfile)


def send_result_notication(recipient, title, status, message):
    """Send email notification. """
    replaces = {
        "title": title,
        "status": status,
        "message": message
    }
    body = get_html_template("data_extraction_result.html", replaces)
    send_mail(
        body,
        "MeteoHub: data extraction completed",
        recipient,
        plain_body=body
    )


def human_size(bytes, units=[' bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB']):
    """ Returns a human readable string reprentation of bytes
    :rtype: string
    """
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])


def adapt_reftime(schedule, reftime):
    new_reftime = None
    if reftime is not None:
        new_reftime = {}
        now = datetime.datetime.utcnow()
        reftime_to = datetime.datetime.strptime(reftime['to'], "%Y-%m-%dT%H:%M:%S.%fZ")
        submission_date = schedule.submission_date
        time_delta_to = submission_date - reftime_to
        time_delta_from = schedule.time_delta
        new_reftime_to = now - time_delta_to
        new_reftime_from = new_reftime_to - time_delta_from
        new_reftime['from'] = new_reftime_from.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        new_reftime['to'] = new_reftime_to.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return new_reftime
