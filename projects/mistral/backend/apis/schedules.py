from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from utilities import htmlcodes as hcodes
from utilities.logs import get_logger
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager

log = get_logger(__name__)


class Schedules(EndpointResource):

    @catch_error()
    def post(self):

        user = self.get_current_user()
        criteria = self.get_input()
        self.validate_input(criteria, 'DataScheduling')

        dataset_names = criteria.get('datasets')
        # check for existing dataset(s)
        datasets = arki.load_datasets()
        for ds_name in dataset_names:
            found = next((ds for ds in datasets if ds.get('id', '') == ds_name), None)
            if not found:
                raise RestApiException(
                    "Dataset '{}' not found".format(ds_name),
                    status_code=hcodes.HTTP_BAD_NOTFOUND)

        filters = criteria.get('filters')

        db= self.get_service_instance('sqlalchemy')

        # check if scheduling parameters are correct
        if not self.settings_validation(criteria):
            raise RestApiException(
                "scheduling criteria are not valid",
                status_code=hcodes.HTTP_BAD_REQUEST)


        # parsing period settings
        period_settings = criteria.get('period-settings')
        if period_settings is not None:
            every = str(period_settings.get('every'))
            period = period_settings.get('period')
            log.info("Period settings [{} {}]".format(every, period))

            # get schedule id in postgres database as scheduled request name for mongodb
            name_int = RequestManager.create_schedule_record(db, user, filters, every=every, period=period)
            name = str(name_int)

            # remove previous task
            res = CeleryExt.delete_periodic_task(name=name)
            log.debug("Previous task deleted = %s", res)

            request_id = None

            CeleryExt.create_periodic_task(
                name=name,
                task="mistral.tasks.data_extraction.data_extract",
                every=every,
                period=period,
                args=[user.uuid, dataset_names, filters, request_id, name_int],
            )

            log.info("Scheduling periodic task")


        crontab_settings = criteria.get('crontab-settings')
        if crontab_settings is not None:
            # get scheduled request id in postgres database as scheduled request name for mongodb
            name_int =RequestManager.create_schedule_record(db, user, filters, crontab_settings=crontab_settings)
            name = str(name_int)

            # parsing crontab settings
            for i in crontab_settings.keys():
                val = crontab_settings.get(i)
                str_val = str(val)
                crontab_settings[i] = str_val

            request_id = None

            CeleryExt.create_crontab_task(
                name=name,
                task="mistral.tasks.data_extraction.data_extract",
                **crontab_settings,
                args=[user.uuid, dataset_names, filters,request_id, name_int],
            )

            log.info("Scheduling crontab task")

        return self.force_response('Scheduled task {}'.format(name))

    @staticmethod
    def settings_validation(criteria):
        # check if at least one scheduling parameter is in the request
        period_settings = criteria.get('period-settings')
        crontab_settings = criteria.get('crontab-settings')
        if period_settings or crontab_settings is not None:
            return True
        else:
            return False

    @catch_error()
    def get(self, schedule_id=None):
        param = self.get_input()
        sort = param.get('sort-by')
        sort_order = param.get('sort-order')
        get_total = param.get('get_total', False)

        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')
        if schedule_id is not None:
            # get total count for user schedules
            if get_total:
                counter = RequestManager.count_schedule_requests(db, schedule_id)
                return {"total": counter}

            # check if the current user is the owner of the scheduled request
            if not RequestManager.check_owner(db, user.uuid, schedule_id=schedule_id):
                raise RestApiException(
                    "Operation not allowed",
                    status_code=hcodes.HTTP_BAD_UNAUTHORIZED)

            # get submitted requests related to a schedule list
            res = RequestManager.get_schedule_requests(db, schedule_id, sort_by=sort, sort_order=sort_order)

        else:
            # get total count for user schedules
            if get_total:
                counter = RequestManager.count_user_schedules(db, user.uuid)
                return {"total": counter}
            # get user requests list
            res = RequestManager.get_user_schedules(db, user.uuid, sort_by=sort, sort_order=sort_order)


        return self.force_response(
            res, code=hcodes.HTTP_OK_BASIC)

    @catch_error()
    def patch(self, schedule_id):
        param = self.get_input()
        is_active = param.get('is_active')
        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')

        #check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db,user.uuid,schedule_id)

        # disable/enable the schedule
        periodic = CeleryExt.get_periodic_task(name=schedule_id)
        periodic.update(enabled=is_active)

        # update schedule status in database
        RequestManager.update_schedule_status(db, schedule_id, is_active)

        return self.force_response(
            "Schedule {}: enabled = {}".format(schedule_id,is_active), code=hcodes.HTTP_OK_BASIC)

    @catch_error()
    def delete(self, schedule_id):
        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')

        # check if the schedule exist and is owned by the current user
        self.request_and_owner_check(db, user.uuid, schedule_id)

        # delete schedule in mongodb
        CeleryExt.delete_periodic_task(name=schedule_id)

        # delete schedule status in database
        RequestManager.delete_schedule(db, schedule_id)

        return self.force_response(
            "Schedule {} succesfully deleted".format(schedule_id), code=hcodes.HTTP_OK_BASIC)


    @staticmethod
    def request_and_owner_check(db,uuid,schedule_id):
        # check if the schedule exists
        if not RequestManager.check_request(db, schedule_id=schedule_id):
            raise RestApiException(
                "The request doesn't exist",
                status_code=hcodes.HTTP_BAD_NOTFOUND)

        # check if the current user is the owner of the request
        if not RequestManager.check_owner(db, uuid, schedule_id=schedule_id):
            raise RestApiException(
                "This request doesn't come from the request's owner",
                status_code=hcodes.HTTP_BAD_UNAUTHORIZED)