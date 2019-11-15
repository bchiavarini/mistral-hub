from restapi.rest.definition import EndpointResource
from restapi.flask_ext.flask_celery import CeleryExt
from restapi.exceptions import RestApiException
from restapi.decorators import catch_error
from restapi.protocols.bearer import authentication
from restapi.utilities.htmlcodes import hcodes
from mistral.services.arkimet import BeArkimet as arki
from mistral.services.requests_manager import RequestManager

from utilities.logs import get_logger

log = get_logger(__name__)


class ScheduledData(EndpointResource):

    # schema_expose = True
    labels = ['scheduled']
    POST = {'/data/scheduled': {'summary': 'Request for data extraction.', 'parameters': [{'name': 'scheduled_criteria', 'in': 'body', 'description': 'Criteria for scheduled data extraction.', 'schema': {'$ref': '#/definitions/DataScheduling'}}], 'responses': {'204': {'description': 'no response given'}, '400': {'description': 'scheduling criteria are not valid'}}}}
    DELETE = {'/data/scheduled': {'summary': 'Request for task deletion.', 'parameters': [{'name': 'task', 'in': 'query', 'description': 'Task to remove.', 'type': 'string', 'required': True}], 'responses': {'200': {'description': 'Task deleted'}, '404': {'description': 'Task not found'}, '401': {'description': 'The user is not the owner of the request to delete'}}}}

    @catch_error()
    @authentication.required()
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
            # get scheduled request id in postgres database as scheduled request name for mongodb
            name_int = RequestManager.create_scheduled_request_record(db, user, filters, every=every, period=period)
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
                args=[user.id, dataset_names, filters, request_id, name_int],
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

            CeleryExt.create_crontab_task(
                name=name,
                task="mistral.tasks.data_extraction.data_extract",
                **crontab_settings,
                args=[user.id, dataset_names, filters],
            )

            log.info("Scheduling crontab task")

        return self.force_response('Scheduled task {}'.format(name))

    @catch_error()
    @authentication.required()
    def delete(self):
        param = self.get_input()
        task_name = param.get('task')

        user = self.get_current_user()

        db = self.get_service_instance('sqlalchemy')
        # check if the request exists
        if not RequestManager.check_request(db,schedule_id=task_name):
            raise RestApiException(
                "The request doesn't exist",
                status_code=hcodes.HTTP_BAD_NOTFOUND)

        # check if the current user is the owner of the request
        if RequestManager.check_owner(db,user.id,schedule_id=task_name):
            # delete request entry from database
            RequestManager.disable_schedule_record(db, task_name)

            CeleryExt.delete_periodic_task(name=task_name)

            return self.force_response('Removed task {}'.format(task_name))
        else :
            raise RestApiException(
                "This request doesn't come from the request's owner",
                status_code=hcodes.HTTP_BAD_UNAUTHORIZED)

    @staticmethod
    def settings_validation(criteria):
        # check if at least one scheduling parameter is in the request
        period_settings = criteria.get('period-settings')
        crontab_settings = criteria.get('crontab-settings')
        if period_settings or crontab_settings is not None:
            return True
        else:
            return False