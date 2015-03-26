"""
Module that holds all model-related actions

Classes
-------
MakeSkymodelFromModelImage : Action
    Makes a sky model from a CASA model image
MakeFacetSkymodel : Action
    Makes a sky model for a facet
MergeSkymodels : Action
    Merges two sky models
FFT : Action
    FFTs a model into an MS

"""

from factor.lib.action import Action
from factor.lib.action_lib import make_image_basename, getOptimumSize
from jinja2 import Environment, FileSystemLoader
import os

DIR = os.path.dirname(os.path.abspath(__file__))
env = Environment(loader=FileSystemLoader(os.path.join(DIR, 'templates')))


class MakeSkymodelFromModelImage(Action):
    """
    Action to make a sky model from a CASA model image

    Input data maps
    ---------------
    input_datamap : Datamap
        Map of CASA model images

    Output data maps
    ----------------
    output_datamap : Datamap
        Map of sky model files

    """
    def __init__(self, op_parset, input_datamap, p, prefix=None, direction=None,
        clean=True, index=None):
        """
        Create action and run pipeline

        Parameters
        ----------
        op_parset : dict
            Parset dict of the calling operation
        input_datamap : data map
            Input data map for CASA model image
        p : dict
            Input parset dict defining model and pipeline parameters
        prefix : str, optional
            Prefix to use for model names
        direction : Direction object, optional
            Direction for this model
        clean : bool, optional
            Remove unneeded files?
        index : int, optional
            Index of action

        """
        super(MakeSkymodelFromModelImage, self).__init__(op_parset,
            'MakeSkymodelFromModelImage', prefix=prefix, direction=direction,
            index=index)

        # Store input parameters
        self.input_datamap = input_datamap
        self.p = p.copy()
        if self.prefix is None:
            self.prefix = 'make_skymodel'
        self.clean = clean
        self.working_dir = self.model_dir + '{0}/{1}/'.format(self.op_name, self.name)
        if self.direction is not None:
            self.working_dir += '{0}/'.format(self.direction.name)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        # Define script name
        self.script_file = self.parsetbasename + 'make_skymodel_from_model_image.py'

        # Set up names for output data map
        modelbasenames = make_image_basename(self.input_datamap,
            direction=self.direction)
        self.modelbasenames = [self.working_dir+bn for bn in modelbasenames]

        # Set up all required files
        self.setup()


    def make_datamaps(self):
        """
        Makes the required data maps
        """
        from factor.lib.datamap_lib import read_mapfile
        from factor.lib.action_lib import convert_fits_to_image

        # Input is list of image basenames
        # Output is sky model files
        imagebasenames, hosts = read_mapfile(self.input_datamap)

        if self.op_parset['imager'].lower() == 'wsclean':
            # Convert WSClean model fits images to casapy images
            if self.p['nterms'] > 1:
                input_fits_files = [bn+'-MFS-model.fits' for bn in imagebasenames]
            else:
                input_fits_files = [bn+'-model.fits' for bn in imagebasenames]
            input_files = []
            for f in input_fits_files:
                input_files.append(convert_fits_to_image(f))
        else:
            input_files = [bn+'.model' for bn in imagebasenames]
        output_files = [bn+'.skymodel' for bn in self.modelbasenames]

        self.p['input_datamap'] = self.write_mapfile(input_files,
            prefix=self.prefix+'_input', direction=self.direction,
            index=self.index, host_list=hosts)

        self.p['output_datamap'] = self.write_mapfile(output_files,
            prefix=self.prefix+'_output', direction=self.direction,
            index=self.index, host_list=hosts)


    def make_pipeline_control_parset(self):
        """
        Writes the pipeline control parset and any script files
        """
        if 'ncpu' not in self.p:
            self.p['ncpu'] = self.max_cpu

        self.p['scriptname'] = os.path.abspath(self.script_file)
        self.p['outputdir'] = os.path.abspath(self.working_dir)
        template = env.get_template('make_skymodel_from_model_image.pipeline.parset.tpl')
        tmp = template.render(self.p)
        with open(self.pipeline_parset_file, 'w') as f:
            f.write(tmp)

        template = env.get_template('make_skymodel_from_model_image.tpl')
        tmp = template.render(self.p)
        with open(self.script_file, 'w') as f:
            f.write(tmp)


    def get_results(self):
        """
        Return skymodel names.

        If a skymodel was not made because there were no sources in the facet,
        set the skip flag to True.

        """
        return self.p['output_datamap']


class MakeFacetSkymodel(Action):
    """
    Action to make a sky model for a facet

    Input data maps
    ---------------
    input_datamap : Datamap
        Map of full sky model files

    Output data maps
    ----------------
    output_datamap : Datamap
        Map of facet sky model files

    """
    def __init__(self, op_parset, input_datamap, p, direction, prefix=None,
        clean=True, index=None, cal_only=True):
        """
        Create action and run pipeline

        Parameters
        ----------
        op_parset : dict
            Parset dict of the calling operation
        input_datamap : data map
            Input data map for full sky models
        p : dict
            Input parset dict defining model and pipeline parameters
        direction : Direction object
            Direction for this model
        prefix : str, optional
            Prefix to use for model names
        clean : bool, optional
            Remove unneeded files?
        index : int, optional
            Index of action
        cal_only : bool, optional
            If True, return sky model for calibrator only. If False, return
            sky model for entire facet

        """
        super(MakeFacetSkymodel, self).__init__(op_parset, 'MakeFacetSkymodel',
            prefix=prefix, direction=direction, index=index)

        # Store input parameters
        self.input_datamap = input_datamap
        self.p = p.copy()
        if self.prefix is None:
            self.prefix = 'make_facet_skymodel'
        self.clean = clean
        self.cal_only = cal_only
        self.working_dir = self.model_dir + '{0}/{1}/'.format(self.op_name, self.name)
        self.working_dir += '{0}/'.format(self.direction.name)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        # Define script name
        self.script_file = self.parsetbasename + 'make_facet_skymodels.py'

        # Set up names for output data map
        modelbasenames = make_image_basename(self.input_datamap,
            direction=self.direction, prefix=self.prefix)
        self.modelbasenames = [self.working_dir+bn for bn in modelbasenames]

        # Set up all required files
        self.setup()


    def make_datamaps(self):
        """
        Makes the required data maps
        """
        from factor.lib.datamap_lib import read_mapfile

        self.p['input_datamap'] = self.input_datamap

        basenames, hosts = read_mapfile(self.input_datamap)
        output_files = [bn + '_facet.skymodel' for bn in self.modelbasenames]
        self.p['output_datamap'] = self.write_mapfile(output_files,
            prefix=self.prefix+'_output', direction=self.direction,
            index=self.index, host_list=hosts)


    def make_pipeline_control_parset(self):
        """
        Writes the pipeline control parset and any script files
        """
        if 'ncpu' not in self.p:
            self.p['ncpu'] = self.max_cpu
        self.p['scriptname'] = os.path.abspath(self.script_file)
        self.p['cal_only'] = self.cal_only
        self.p['vertices'] = self.direction.vertices
        self.p['ra'] = self.direction.ra
        self.p['dec'] = self.direction.dec
        self.p['cal_radius'] = self.direction.cal_radius_deg

        template = env.get_template('make_facet_skymodel.pipeline.parset.tpl')
        tmp = template.render(self.p)
        with open(self.pipeline_parset_file, 'w') as f:
            f.write(tmp)

        template = env.get_template('make_facet_skymodel.tpl')
        tmp = template.render(self.p)
        with open(self.script_file, 'w') as f:
            f.write(tmp)


    def get_results(self):
        """
        Return skymodel names
        """
        from factor.lib.datamap_lib import read_mapfile, set_mapfile_flags

        model_files, hosts = read_mapfile(self.p['output_datamap'])
        skip_flags = []
        for model_file in model_files:
            if not os.path.exists(model_file):
                skip_flags.append(True)
            else:
                skip_flags.append(False)
        set_mapfile_flags(self.p['output_datamap'], skip_flags)

        return self.p['output_datamap']


class MergeSkymodels(Action):
    """
    Action to merge two sky models

    Input data maps
    ---------------
    skymodel1_datamap : Datamap
        Map of sky models
    skymodel2_datamap : Datamap
        Map of sky models

    Output data maps
    ----------------
    output_datamap : Datamap
        Map of merged sky model files

    """
    def __init__(self, op_parset, skymodel1_datamap, skymodel2_datamap, p, prefix=None,
        direction=None, clean=True, index=None):
        """
        Create action and run pipeline

        Parameters
        ----------
        op_parset : dict
            Parset dict of the calling operation
        skymodel1_datamap : data map
            Input data map for model 1
        skymodel2_datamap : data map
            Input data map for model 2
        p : dict
            Input parset dict defining model and pipeline parameters
        prefix : str, optional
            Prefix to use for model names
        direction : Direction object, optional
            Direction for this model
        clean : bool, optional
            Remove unneeded files?
        index : int, optional
            Index of action

        """
        super(MergeSkymodels, self).__init__(op_parset, 'MergeSkymodels',
            prefix=prefix, direction=direction, index=index)

        # Store input parameters
        self.skymodel1_datamap = skymodel1_datamap
        self.skymodel2_datamap = skymodel2_datamap
        self.p = p.copy()
        if self.prefix is None:
            self.prefix = 'merge_skymodel'
        self.clean = clean
        self.working_dir = self.model_dir + '{0}/{1}/'.format(self.op_name, self.name)
        if self.direction is not None:
            self.working_dir += '{0}/'.format(self.direction.name)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        # Define script name
        self.script_file = self.parsetbasename + 'merge_skymodels.py'

        # Set up all required files
        self.setup()


    def make_datamaps(self):
        """
        Makes the required data maps
        """
        from factor.lib.datamap_lib import read_mapfile

        self.p['skymodel1_datamap'] = self.skymodel1_datamap
        self.p['skymodel2_datamap'] = self.skymodel2_datamap

        model1basenames, hosts = read_mapfile(self.skymodel1_datamap)
        output_files = [os.path.splitext(bn)[0] + '_merged.skymodel' for bn in
            model1basenames]

        self.p['output_datamap'] = self.write_mapfile(output_files,
            prefix=self.prefix+'_output', direction=self.direction,
            index=self.index, host_list=hosts)


    def make_pipeline_control_parset(self):
        """
        Writes the pipeline control parset and any script files
        """
        if 'ncpu' not in self.p:
            self.p['ncpu'] = self.max_cpu
        self.p['mergescriptname'] = os.path.abspath(self.script_file)

        template = env.get_template('merge_skymodels.pipeline.parset.tpl')
        tmp = template.render(self.p)
        with open(self.pipeline_parset_file, 'w') as f:
            f.write(tmp)

        template = env.get_template('merge_skymodels.tpl')
        tmp = template.render(self.p)
        with open(self.script_file, 'w') as f:
            f.write(tmp)


    def get_results(self):
        """
        Return skymodel names
        """
        return self.p['output_datamap']


class FFT(Action):
    """
    Action to FFT a model into a vis column of an MS

    Input data maps
    ---------------
    vis_datamap : Datamap
        Map of vis data
    model_datamap : Datamap
        Map of CASA model images

    Output data maps
    ----------------
    None

    """
    def __init__(self, op_parset, vis_datamap, model_basenames_datamap, p, prefix=None,
    	direction=None, band=None, clean=True, index=None):
        """
        Create action and run pipeline

        Parameters
        ----------
        op_parset : dict
            Parset dict of the calling operation
        vis_datamap : data map
            Input data map for vis data
        model_basenames_datamap : data map
            Input data map for model basenames
        p : dict
            Input parset dict defining model and pipeline parameters
        prefix : str, optional
            Prefix to use for model names
        direction : Direction object, optional
            Direction for this model
        band : Band object, optional
            Band for this model
        clean : bool, optional
            Remove unneeded files?
        index : int, optional
            Index of action

        """
        super(FFT, self).__init__(op_parset, 'FFT', prefix=prefix,
        	direction=direction, band=band, index=index)

        # Store input parameters
        self.vis_datamap = vis_datamap
        self.model_datamap = model_basenames_datamap
        self.p = p.copy()
        if self.prefix is None:
            self.prefix = 'fft'
        self.clean = clean
        self.working_dir = self.model_dir + '{0}/{1}/'.format(self.op_name, self.name)
        if self.direction is not None:
            self.working_dir += '{0}/'.format(self.direction.name)
            self.p['imsize'] = getOptimumSize(int(self.direction.imsize))
        if self.band is not None:
            self.working_dir += '{0}/'.format(self.band.name)
        if not os.path.exists(self.working_dir):
            os.makedirs(self.working_dir)

        # Define script and task files
        self.script_file = self.parsetbasename + 'ftw.py'
        self.task_xml_file = os.path.join(self.parset_dir, 'ftw.xml')
        self.task_py_file = os.path.join(self.parset_dir, 'task_ftw.py')

        # Set up wplanes
        if 'wplanes' not in self.p:
            self.setup_wplanes()

        # Set a timeout for casapy runs
        if self.op_parset['imager'].lower() == 'casapy':
            self.timeout = 1200

        # Set up all required files
        self.setup()


    def setup_wplanes(self):
        """
        Set up wplanes from imsize
        """
        imsizep = self.p['imsize']

        wplanes = 1
        if imsizep > 512:
            wplanes = 64
        if imsizep > 799:
            wplanes = 96
        if imsizep > 1023:
            wplanes = 128
        if imsizep > 1599:
            wplanes = 256
        if imsizep > 2047:
            wplanes = 384
        if imsizep > 3000:
            wplanes = 448
        if imsizep > 4095:
            wplanes = 512

        self.p['wplanes'] = wplanes


    def make_datamaps(self):
        """
        Makes the required data maps
        """
        self.p['vis_datamap'] = self.vis_datamap
        self.p['model_datamap'] = self.model_datamap


    def make_pipeline_control_parset(self):
        """
        Writes the pipeline control parset and any script files
        """
        if 'ncpu' not in self.p:
            self.p['ncpu'] = self.max_cpu
        self.p['scriptname'] = os.path.abspath(self.script_file)
        self.p['imagerroot'] = self.op_parset['imagerroot']

        if self.op_parset['imager'].lower() == 'awimager':
            template = env.get_template('fft_awimager.pipeline.parset.tpl')
        elif self.op_parset['imager'].lower() == 'casapy':
            template = env.get_template('fft_casapy.pipeline.parset.tpl')
        elif self.op_parset['imager'].lower() == 'wsclean':
            template = env.get_template('fft_wsclean.pipeline.parset.tpl')
            self.p['cell_deg'] = float(self.p['cell'].split('arcsec')[0]) / 3600.0

        tmp = template.render(self.p)
        with open(self.pipeline_parset_file, 'w') as f:
            f.write(tmp)

        if self.op_parset['imager'].lower() == 'casapy':
            # Make ftw.xml and task_ftw.py files needed for custom task in casapy
            self.p['task_xml_file'] = self.task_xml_file
            template = env.get_template('ftw.xml.tpl')
            tmp = template.render(self.p)
            with open(self.task_xml_file, 'w') as f:
                f.write(tmp)

            self.p['task_py_file'] = self.task_py_file
            template = env.get_template('task_ftw.tpl')
            tmp = template.render(self.p)
            with open(self.task_py_file, 'w') as f:
                f.write(tmp)

            template = env.get_template('ftw.tpl')
            tmp = template.render(self.p)
            with open(self.script_file, 'w') as f:
                f.write(tmp)


    def get_results(self):
        """
        Returns results
        """
        return None


    def clean(self):
        """
        Remove unneeded files:

        """
        pass

