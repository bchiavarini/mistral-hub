# -*- coding: utf-8 -*-

from flask import request
from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.services.uploader import Uploader
from restapi.confs import UPLOAD_FOLDER
from restapi.utilities.htmlcodes import hcodes
from restapi.utilities.logs import log
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager as repo

import os
import shutil
from zipfile import ZipFile
from pathlib import Path


class Data(EndpointResource, Uploader):
    # schema_expose = True
    labels = ['data']
    POST = {
        '/data': {
            'summary': 'Request for data extraction.',
            'parameters': [
                {
                    'name': 'criteria',
                    'in': 'body',
                    'description': 'Criteria for data extraction.',
                    'schema': {'$ref': '#/definitions/DataExtraction'},
                }
            ],
            'responses': {
                '202': {
                    'description': 'Data extraction request queued'
                },
                '400': {
                    'description': 'Parameters for post processing are not correct'
                },
                '500': {
                    'description': 'File for spare point interpolation post processor is corrupted'
                }
            },
        }
    }
    PATCH = {
        '/data': {
            'summary': 'Uploading file for spare point interpolation postprocessor',
            'consumes': ['multipart/form-data'],
            'parameters': [
                {
                    'name': 'file',
                    'in': 'formData',
                    'description': 'spare point file for the interpolation',
                    'type': 'file'
                }
            ],
            'responses': {
                '202': {
                    'description': 'file uploaded',
                    'schema': {'$ref': '#/definitions/SparePointFile'}
                },
                '400': {
                    'description': 'file cannot be uploaded'
                }
            },
        }
    }

    @catch_error()
    @authentication.required()
    def post(self):

        user = self.get_current_user()
        log.info(
            'request for data extraction coming from user UUID: {}'.format(user.uuid)
        )
        criteria = self.get_input()

        self.validate_input(criteria, 'DataExtraction')
        product_name = criteria.get('name')
        dataset_names = criteria.get('datasets')
        reftime = criteria.get('reftime')
        if reftime is not None:
            # 'from' and 'to' both mandatory by schema
            # check from <= to
            if reftime['from'] > reftime['to']:
                raise RestApiException(
                    'Invalid reftime: <from> greater than <to>',
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )
        # check for existing dataset(s)
        datasets = arki.load_datasets()
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get('id', '') == ds_name), None)
            if not found:
                raise RestApiException(
                    "Dataset '{}' not found".format(ds_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND,
                )
        # incoming filters: <dict> in form of filter_name: list_of_values
        # e.g. 'level': [{...}, {...}] or 'level: {...}'
        filters = criteria.get('filters', {})
        # clean up filters from unknown values
        filters = {k: v for k, v in filters.items() if arki.is_filter_allowed(k)}

        processors = criteria.get('postprocessors', [])
        # clean up processors from unknown values
        # processors = [i for i in processors if arki.is_processor_allowed(i.get('type'))]
        for p in processors:
            p_type = p.get('type')
            if p_type == 'derived_variables':
                self.validate_input(p, 'AVProcessor')
            elif p_type == 'grid_interpolation':
                self.validate_input(p, 'GIProcessor')
                self.get_trans_type(p)
            elif p_type == 'grid_cropping':
                self.validate_input(p, 'GCProcessor')
                p['trans-type'] = "zoom"
            elif p_type == 'spare_point_interpolation':
                self.validate_input(p, 'SPIProcessor')
                self.get_trans_type(p)
                self.validate_spare_point_interpol_params(p)
            elif p_type == 'statistic_elaboration':
                self.validate_input(p, 'SEProcessor')
                self.validate_statistic_elaboration_params(p)
            else:
                raise RestApiException(
                    'Unknown post-processor type for {}'.format(p_type),
                    status_code=hcodes.HTTP_BAD_REQUEST,
                )

        # run the following steps in a transaction
        db = self.get_service_instance('sqlalchemy')
        try:
            request = repo.create_request_record(
                db,
                user.id,
                product_name,
                {
                    'datasets': dataset_names,
                    'reftime': reftime,
                    'filters': filters,
                    'postprocessors': processors,
                },
            )

            task = CeleryExt.data_extract.apply_async(
                args=[user.id, dataset_names, reftime, filters, processors, request.id],
                countdown=1,
            )

            request.task_id = task.id
            request.status = task.status  # 'PENDING'
            db.session.commit()
            log.info('Request successfully saved: <ID:{}>', request.id)
        except Exception as error:
            db.session.rollback()
            raise SystemError("Unable to submit the request")

        # return self.force_response(
        #     {'task_id': task.id, 'task_status': task.status}, code=hcodes.HTTP_OK_ACCEPTED)
        return self.empty_response()

    @catch_error()
    @authentication.required()
    def patch(self):
        user = self.get_current_user()
        # allowed formats for uploaded file
        self.allowed_exts = ['shp', 'shx', 'geojson','dbf', 'zip', 'grib']
        request_file = request.files['file']
        f = request_file.filename.rsplit(".", 1)

        # check if the shapefile in the zip folder is complete
        if f[1]== 'zip':
            with ZipFile(request_file, 'r') as zip:
                uploaded_files = zip.namelist()
                self.check_files_to_upload(uploaded_files)
            request.files['file'].seek(0)

        # upload the files
        upload_response = self.upload(subfolder=user.uuid)

        if not upload_response.defined_content:
            raise RestApiException(
                upload_response.errors,
                status_code=hcodes.HTTP_BAD_REQUEST,
            )

        upload_filename = upload_response.defined_content['filename']
        upload_filepath = os.path.join(UPLOAD_FOLDER, user.uuid, upload_filename)
        log.debug('File uploaded. Filepath : {}', upload_filepath)

        # if the file is a zip file extract the content in the upload folder
        if f[1] == 'zip':
            files = []
            with ZipFile(upload_filepath, 'r') as zip:
                files = zip.namelist()
                log.debug('filelist: {}'.format(files))
                upload_folder = Path(upload_filepath).parent
                zip.extractall(path=upload_folder)
            # get .shp file filename
            for f in files:
                e = f.rsplit(".", 1)
                if e[1] == 'shp':
                    upload_filepath = os.path.join(UPLOAD_FOLDER, user.uuid, f)
        r = {}
        filename = self.split_dir_and_extension(upload_filepath)
        r['filepath'] = upload_filepath
        r['format'] = filename[1]
        return self.force_response(r)

    @staticmethod
    def get_trans_type(params):
        # get trans-type according to the sub-type coming from the request
        sub_type = params['sub-type']
        if sub_type in ("near", "bilin"):
            params['trans-type'] = "inter"
        if sub_type in ("average", "min", "max"):
            if params['type'] == 'grid_interpolation':
                params['trans-type'] = "boxinter"
            else:
                params['trans-type'] = "polyinter"

    @staticmethod
    def validate_spare_point_interpol_params(params):
        coord_filepath = params['coord-filepath']
        if not os.path.exists(coord_filepath):
            raise RestApiException('the coord-filepath does not exists',
                                   status_code=hcodes.HTTP_BAD_REQUEST)

        filebase, fileext = os.path.splitext(coord_filepath)
        if fileext.strip('.') != params['format']:
            raise RestApiException('format parameter is not correct',
                                   status_code=hcodes.HTTP_BAD_REQUEST)
        # if a file is a shapefile, check if .shx and .dbf are in the same folder. If not ask the user to upload all the files again
        if params['format'] == 'shp':
            if not os.path.exists(filebase + '.shx') or not os.path.exists(filebase + '.dbf'):
                # delete the folder with the corrupted files
                uploaded_filepath = Path(params['coord-filepath'])
                shutil.rmtree(uploaded_filepath.parent)
                raise RestApiException('Sorry.The file for the interpolation is corrupted. Please try to upload it again',
                                       status_code=hcodes.HTTP_SERVER_ERROR)

    @staticmethod
    def validate_statistic_elaboration_params(params):
        input = params['input-timerange']
        output = params['output-timerange']
        if input != output:
            if input == 254:
                if output == 1:
                    raise RestApiException(
                        'Parameters for statistic elaboration are not correct',
                        status_code=hcodes.HTTP_BAD_REQUEST)
                else:
                    return
            if input == 0:
                if output != 254:
                    raise RestApiException(
                        'Parameters for statistic elaboration are not correct',
                        status_code=hcodes.HTTP_BAD_REQUEST)
                else:
                    return
            else:
                raise RestApiException(
                    'Parameters for statistic elaboration are not correct',
                    status_code=hcodes.HTTP_BAD_REQUEST)
        if input == output:
            if input == 254:
                raise RestApiException(
                    'Parameters for statistic elaboration are not correct',
                    status_code=hcodes.HTTP_BAD_REQUEST)

    @staticmethod
    def check_files_to_upload(files):
        # create a dictionary to compare the uploaded files specs
        file_dict = {}
        for f in files:
            e = f.rsplit(".", 1)
            file_dict[e[1]] = e[0]
        if 'shp' in file_dict:
            # check if there is a file .shx and a file .dbf
            if 'shx' not in file_dict:
                raise RestApiException('file .shx is missing',
                                       status_code=hcodes.HTTP_BAD_REQUEST)
            if 'dbf' not in file_dict:
                raise RestApiException('file .dbf is missing',
                                       status_code=hcodes.HTTP_BAD_REQUEST)
            # check if the file .shx and the file .dbf are for the .shp file
            if file_dict['shp'] != file_dict['shx']:
                raise RestApiException('file .shx and file .shp does not match',
                                       status_code=hcodes.HTTP_BAD_REQUEST)
            if file_dict['shp'] != file_dict['dbf']:
                raise RestApiException('file .dbf and file .shp does not match',
                                       status_code=hcodes.HTTP_BAD_REQUEST)
