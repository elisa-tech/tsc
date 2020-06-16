# SPDX-FileCopyrightText: 2020 Bayerische Motoren Werke Aktiengesellschaft (BMW AG)
#
# SPDX-License-Identifier: Apache-2.0

import pickle


class GraphDb(dict):
    """GraphDb to store the graphs.
    """

    def __init__(self, file_name):
        self._file_name = file_name
        return

    def save(self):
        if self._file_name == "":
            raise(NameError("Cannot save. File name not set."))

        with open(self._file_name, 'wb') as stream:
            pickle.dump(self, stream, protocol=pickle.HIGHEST_PROTOCOL)

    def open(self):
        if self._file_name == "":
            raise(NameError("Cannot open. File name not set."))

        self.clear()
        with open(self._file_name, 'rb') as stream:
            self.update(pickle.load(stream))

    def normalize_paths(self, depth=0):
        if depth <= 0:
            return
        for key, value_list in self.items():
            key.normalize_path(depth)
            for value in value_list:
                value.normalize_path(depth)
