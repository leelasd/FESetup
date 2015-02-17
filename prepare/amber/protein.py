#  Copyright (C) 2012-2014  Hannes H Loeffler
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#  For full details of the license please see the COPYING file
#  that should have come with this distribution.

r"""
A class to build a protein receptor with FESetup.  Derives from Common.

The protein Setup class protonates and creates AMBER topology and
coordinate files based on a single coordinate input file.
"""

__revision__ = "$Id$"



import os

import FESetup
from FESetup import const, errors, logger
from common import *
import utils


class Protein(Common):
    """The protein setup class."""


    def __init__(self, protein_name, basedir, start_file = 'protein.pdb',
                 overwrite = False):
        """
        :param protein_name: name of the protein, will be used as directory name
        :type protein_name: string
        :param basedir: base directory containing start_file
        :type basedir: string
        :param start_file: the file name of the protein
        :type start_file: string
        :param overwrite: overwrite files in the working directory from basedir
        :type overwrite: string
        :raises: SetupError
        """

        self.workdir = const.PROTEIN_WORKDIR

        super(Protein, self).__init__(protein_name, basedir, self.workdir,
                                      overwrite)

        sfile = os.path.join(basedir, protein_name, start_file)

        if not os.access(sfile, os.R_OK):
            raise errors.SetupError('the protein start file %s does not exist '
                                    % sfile)

        self.mol_file = start_file
        self.mol_fmt = 'pdb'


    # import force field independent functionality (to avoid mixins)
    from FESetup.prepare.protutil import protonate_propka


    @report
    def get_charge(self):
        """
        Get the protein charge via leap.

        :raises: SetupError
        """

        charge_file = os.path.join(self.dst, const.CHARGE_FILE)

        if not os.access(charge_file, os.R_OK):
            mol_file = os.path.join(self.dst, self.mol_file)

            if not os.access(mol_file, os.R_OK):
                raise errors.SetupError('the protein start file %s does not exist '
                                        % mol_file)
        
            out = utils.run_leap('', '', 'tleap',
                                 '%s\np = loadpdb %s\ncharge p\n' %
                                 (self.ff_cmd, mol_file) )

            charge = None

            for line in out.split('\n'):
                if 'Total unperturbed charge:' in line[0:]:
                    charge = line.split(':')[1]
                    break

            if charge:
                try:
                    self.charge = float(charge)
                except ValueError:
                    raise errors.SetupError('Cannot convert charge from string: %s'
                                            % charge)
            else:
                raise errors.SetupError('leap cannot compute charge')

            with open(charge_file, 'w') as chf:
                chf.write('%s' % self.charge)
        else:                           # cache it
            with open(charge_file, 'r') as chf:
                self.charge = float(chf.read() )

        logger.write('Protein charge: %.3f' % self.charge)


    @report
    def create_top(self, boxtype = '', boxlength = 10.0, boxfile = None,
                   align = False, neutralize = False, addcmd = '',
                   addcmd2 = ''):
        """
        Generate an AMBER topology file via leap.

        :param boxtype: rectangular, octahedron or set (set dimensions explicitly)
        :param boxlength: side length of the box
        :param boxfile: name of file containing box dimensions
        :param align: align solute along the principal axes
        :param neutralize: neutralise the system
        :type boxtype: string
        :type boxlength: float
        :type boxfile: string
        :type align: bool
        :type neutralize: bool
        :raises: SetupError
        """


        if os.access(const.LEAP_IN, os.F_OK):
            self.amber_top = const.LEAP_IN + self.TOP_EXT
            self.amber_crd = const.LEAP_IN + self.RST_EXT
            self.amber_pdb = const.LEAP_IN + const.PDB_EXT

            utils.run_leap(self.amber_top, self.amber_crd, program = 'tleap',
                     script = const.LEAP_IN)

            return

        leapin = '''
%s
%s
%s
s = loadpdb "%s"\n
%s''' % (self.ff_cmd, self.solvent_load, addcmd, self.mol_file, addcmd2)

        leapin += self._amber_top_common(boxtype, boxlength, boxfile, align,
                                         neutralize)

        utils.run_leap(self.amber_top, self.amber_crd, 'tleap', leapin)