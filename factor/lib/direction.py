"""
Definition of the direction class
"""
import os
import logging

class Direction(object):
    """
    Generic direction class
    """
    def __init__(self, name, ra, dec, atrous_do, mscale_field_do, cal_imsize,
        solint_p, solint_a, field_imsize, dynamic_range, region_selfcal,
        region_field, peel_skymodel, outlier_do, factor_working_dir,
        make_final_image=False, cal_radius_deg=None, cal_flux_jy=None):
        """
        Create Direction object

        Parameters
        ----------
        name : str
            Name of direction
        ra : float
            RA in degrees of direction center
        dec : float
            Dec in degrees of direction center
        atrous_do : bool
            Fit to wavelet images in PyBDSM?
        mscale_field_do : bool
            Use multiscale clean for facet field?
        cal_imsize : int
            Size of calibrator image in 1.5 arcsec pixels
        solint_p : int
            Solution interval for phase calibration (# of time slots)
        solint_a : int
            Solution interval for amplitude calibration (# of time slots)
        field_imsize : int
            Size of facet image in 1.5 arcsec pixels
        dynamic_range : bool
            LD (low dynamic range) or HD (high dynamic range)
        region_selfcal : str
            Region for clean mask for calibrator selfcal
        region_field : str
            Region for clean mask for facet image
        peel_skymodel : str
            Sky model for peeling
        outlier_do : bool
            If True, peel source without selfcal
        factor_working_dir : str
            Full path of working directory
        make_final_image : bool, optional
            Make final image of this direction, after all directions have been
            selfcaled?
        cal_radius_deg : float, optional
            Radius in degrees of calibrator source
        cal_flux_jy : float, optional
            Apparent flux in Jy of calibrator source
        """
        from factor.operations.hardcoded_param import facet_selfcal as p

        self.name = name
        self.ra = ra
        self.dec = dec
        self.atrous_do = atrous_do
        self.mscale_field_do = mscale_field_do

        self.cal_imsize = cal_imsize
        if cal_radius_deg is None:
            cell = float(p['imager0']['cell'].split('arcsec')[0]) # arcsec per pixel
            self.cal_radius_deg = cal_imsize * cell / 3600.0 / 1.5
        else:
            self.cal_radius_deg = cal_radius_deg

        self.solint_p = solint_p
        self.solint_a = solint_a
        self.field_imsize = field_imsize
        self.dynamic_range = dynamic_range
        self.loop_amp_selfcal = False
        self.improving = True # Whether selfcal is still improving after first amp cal
        self.max_residual_val = 0.5 # maximum residual in Jy for facet subtract test

        self.region_selfcal = region_selfcal
        if self.region_selfcal.lower() == 'empty':
            self.region_selfcal = None

        self.region_field = region_field
        if self.region_field.lower() == 'empty':
            self.region_field = None

        self.peel_skymodel = peel_skymodel
        if self.peel_skymodel.lower() == 'empty':
            self.peel_skymodel = None

        self.outlier_do = outlier_do
        self.make_final_image = make_final_image
        if cal_flux_jy is not None:
            self.apparent_flux_mjy = cal_flux_jy * 1000.0
        else:
            self.apparent_flux_mjy = None
        self.nchannels = 1

        self.working_dir = factor_working_dir
        self.completed_operations = []
        self.save_file = os.path.join(self.working_dir, 'state',
            self.name+'_save.pkl')
        self.pipeline_dir = os.path.join(self.working_dir, 'pipeline')


    def save_state(self):
        """
        Saves the direction state to a file
        """
        import pickle

        with open(self.save_file, 'wb') as f:
            pickle.dump(self.__dict__, f)


    def load_state(self):
        """
        Loads the direction state from a file

        Returns
        -------
        success : bool
            True if state was successfully loaded, False if not
        """
        import pickle

        try:
            with open(self.save_file, 'r') as f:
                self.__dict__ = pickle.load(f)
            return True
        except:
            return False


    def reset_state(self):
        """
        Resets the direction state to initial state to allow reprocessing
        """
        import glob

        operations = ['FacetSelfcal', 'FacetImage', 'FacetCheck']
        for op in operations:
            # Remove entry in completed_operations
            self.completed_operations.remove(op)

            # Delete pipeline state
            action_dirs = glob.glob(os.path.join(self.pipeline_dir, op, '*'))
            for action_dir in action_dirs:
                facet_dir = os.path.join(action_dir, self.name)
                if os.path.exists(facet_dir):
                    os.system('rm -rf {0}'.format(facet_dir))

        self.save_state()

