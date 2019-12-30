import subprocess

from restapi.utilities.logs import get_logger
from mistral.exceptions import PostProcessingException

logger = get_logger(__name__)


def get_trans_type(params):
    # get trans-type according to the sub-type coming from the request
    sub_type = params['sub-type']
    if sub_type in ("near", "bilin"):
        params['trans-type'] = "inter"
    if sub_type in ("average", "min", "max"):
        params['trans-type'] = "boxinter"

def pp_grid_interpolation(params, input, output):
    logger.debug('Grid interpolation postprocessor')
    try:
        post_proc_cmd =[]
        post_proc_cmd.append('vg6d_transform')
        post_proc_cmd.append('--trans-type={}'.format(params.get('trans-type')))
        post_proc_cmd.append('--sub-type={}'.format(params.get('sub-type')))

        # check if there is a grib file template. If not, looks for others interpolation params
        if 'template' in params:
            post_proc_cmd.append('--output-format=grib_api:{}'.format(params['template']))
        else:
            # vg6d_transform automatically provides defaults for missing optional params
            if 'boundings' in params:
                if 'x-min' in params['boundings']:
                    post_proc_cmd.append('--x-min={}'.format(params['boundings']['x-min']))
                if 'x-max' in params['boundings']:
                    post_proc_cmd.append('--x-max={}'.format(params['boundings']['x-max']))
                if 'y-min' in params['boundings']:
                    post_proc_cmd.append('--y-min={}'.format(params['boundings']['y-min']))
                if 'y-max' in params['boundings']:
                    post_proc_cmd.append('--y-max={}'.format(params['boundings']['y-max']))
            if 'nodes' in params:
                if 'nx' in params['nodes']:
                    post_proc_cmd.append('--nx={}'.format(params['nodes']['nx']))
                if 'ny' in params['nodes']:
                    post_proc_cmd.append('--ny={}'.format(params['nodes']['ny']))

        #post_proc_cmd.append('--display')
        post_proc_cmd.append(input)
        post_proc_cmd.append(output)
        logger.debug('Post process command: {}>'.format(post_proc_cmd))

        proc = subprocess.Popen(post_proc_cmd)
        # wait for the process to terminate
        if proc.wait() != 0:
            raise Exception('Failure in post-processing')
        else:
            return output

    except Exception as perr:
        logger.warn(str(perr))
        message = 'Error in post-processing: no results'
        raise PostProcessingException(message)