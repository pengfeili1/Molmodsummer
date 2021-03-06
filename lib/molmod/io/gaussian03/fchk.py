# MolMod is a collection of molecular modelling tools for python.
# Copyright (C) 2007 - 2008 Toon Verstraelen <Toon.Verstraelen@UGent.be>
#
# This file is part of MolMod.
#
# MolMod is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# MolMod is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
# --


from molmod.molecules import Molecule

import numpy

import copy


__all__ = ["ReadError", "FCHKFile"]


class ReadError(Exception):
    pass


class FCHKFile(object):
    def __init__(self, filename, ignore_errors=False, field_labels=None):
        self.filename = filename
        try:
            if field_labels is not None:
                field_labels = set(field_labels)
                field_labels.add("Atomic numbers")
                field_labels.add("Current cartesian coordinates")
            self._read(filename, field_labels)
        except ReadError:
            if ignore_errors:
                pass
            else:
                raise
        self._analyze()

    def _read(self, filename, field_labels=None):
        # if fields is None, all fields are read
        def read_field(f):
            datatype = None
            while datatype is None:
                # find a sane header line
                line = f.readline()
                if line == "":
                    return False

                label = line[:43].strip()
                if field_labels is not None:
                    if len(field_labels) == 0:
                        return False
                    elif label not in field_labels:
                        return True
                    else:
                        field_labels.discard(label)
                line = line[43:]
                words = line.split()

                if words[0] == 'I':
                    datatype = int
                elif words[0] == 'R':
                    datatype = float

            if len(words) == 2:
                try:
                    value = datatype(words[1])
                except ValueError:
                    return True
            elif len(words) == 3:
                if words[1] != "N=":
                    raise ReadError("Unexpected line in formatted checkpoint file %s\n%s" % (filename, line[:-1]))
                length = int(words[2])
                value = numpy.zeros(length, datatype)
                counter = 0
                try:
                    while counter < length:
                        line = f.readline()
                        if line == "":
                            raise ReadError("Unexpected end of formatted checkpoint file %s" % filename)
                        for word in line.split():
                            value[counter] = datatype(word)
                            counter += 1
                except ValueError:
                    return True
            else:
                raise ReadError("Unexpected line in formatted checkpoint file %s\n%s" % (filename, line[:-1]))

            self.fields[label] = value
            return True

        f = file(filename, 'r')
        self.title = f.readline()[:-1]
        words = f.readline().split()
        if len(words) != 3:
            raise ReadError("Second line of FCHKFile is incorrect. Expecting three words.")
        self.command, self.lot, self.basis = words
        self.fields = {}

        while read_field(f):
            pass

        f.close()

    def _analyze(self):
        if ("Atomic numbers" in self.fields) and ("Current cartesian coordinates" in self.fields):
            self.molecule = Molecule(
                self.fields["Atomic numbers"],
                numpy.reshape(self.fields["Current cartesian coordinates"], (-1,3)),
                self.title,
            )

    def get_optimization_energies(self):
        return self.fields.get("Opt point       1 Results for each geome")[::2]

    def get_optimized_enery(self):
        return self.get_optimization_energies()[-1]

    def get_optimization_lowest_index(self):
        return self.get_optimization_energies().argmin()

    def get_optimization_coordinates(self):
        coor_array = self.fields.get("Opt point       1 Geometries")
        if coor_array is None:
            return []
        else:
            return numpy.reshape(coor_array, (-1, len(self.molecule.numbers), 3))

    def get_optimized_molecule(self):
        opt_coor = self.get_optimization_coordinates()
        if len(opt_coor) == 0:
            return None
        else:
            return Molecule(
                self.molecule.numbers,
                opt_coor[-1],
            )

    def get_optimization_gradients(self):
        grad_array = self.fields.get("Opt point       1 Gradient at each geome")
        if grad_array is None:
            return []
        else:
            return numpy.reshape(grad_array, (-1, len(self.molecule.numbers), 3))

    def get_optimized_gradient(self):
        opt_grad = self.get_optimization_gradients()
        if len(opt_grad) == 0:
            return None
        else:
            return opt_grad[-1]

    def get_esp_charges(self):
        return self.fields.get("ESP Charges")

    def get_npa_charges(self):
        return self.fields.get("NPA Charges")

    def get_mulliken_charges(self):
        return self.fields.get("Mulliken Charges")

    def get_gradient(self):
        tmp = self.fields.get("Cartesian Gradient")
        if tmp is None:
            return None
        else:
            return numpy.reshape(tmp, self.molecule.coordinates.shape)

    def get_hessian(self):
        N = len(self.molecule.numbers)
        result = numpy.zeros((3*N,3*N), float)
        counter = 0
        force_const = self.fields["Cartesian Force Constants"]
        for row in xrange(3*N):
            result[row,:row+1] = force_const[counter:counter+row+1]
            result[:row+1,row] = force_const[counter:counter+row+1]
            counter += row + 1
        return result







