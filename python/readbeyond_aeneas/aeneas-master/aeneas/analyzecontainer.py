#!/usr/bin/env python
# coding=utf-8

# aeneas is a Python/C library and a set of tools
# to automagically synchronize audio and text (aka forced alignment)
#
# Copyright (C) 2012-2013, Alberto Pettarin (www.albertopettarin.it)
# Copyright (C) 2013-2015, ReadBeyond Srl   (www.readbeyond.it)
# Copyright (C) 2015-2016, Alberto Pettarin (www.albertopettarin.it)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
This module contains the following classes:

* :class:`~aeneas.analyzecontainer.AnalyzeContainer`
  implementing functions to analyze a given container
  and build the corresponding job object.

.. warning:: This module might be refactored in a future version
"""

from __future__ import absolute_import
from __future__ import print_function
import os
import re

from aeneas.container import Container
from aeneas.hierarchytype import HierarchyType
from aeneas.job import Job
from aeneas.logger import Loggable
from aeneas.runtimeconfiguration import RuntimeConfiguration
from aeneas.task import Task
import aeneas.globalconstants as gc
import aeneas.globalfunctions as gf


class AnalyzeContainer(Loggable):
    """
    Analyze a given container and build the corresponding job.

    :param container: the container to be analyzed
    :type  container: :class:`~aeneas.container.Container`
    :param rconf: a runtime configuration
    :type  rconf: :class:`~aeneas.runtimeconfiguration.RuntimeConfiguration`
    :param logger: the logger object
    :type  logger: :class:`~aeneas.logger.Logger`
    :raises: TypeError: if ``container`` is ``None`` or not an instance of :class:`~aeneas.container.Container`
    """

    TAG = u"AnalyzeContainer"

    def __init__(self, container, rconf=None, logger=None):
        if container is None:
            raise TypeError(u"container is None")
        if not isinstance(container, Container):
            raise TypeError(u"container is not an instance of Container")
        super(AnalyzeContainer, self).__init__(rconf=rconf, logger=logger)
        self.container = container

    def analyze(self, config_string=None):
        """
        Analyze the given container and
        return the corresponding job object.

        On error, it will return ``None``.

        :param string config_string: the configuration string generated by wizard
        :rtype: :class:`~aeneas.job.Job` or ``None``
        """
        try:
            if config_string is not None:
                self.log(u"Analyzing container with the given config string")
                return self._analyze_txt_config(config_string=config_string)
            elif self.container.has_config_xml:
                self.log(u"Analyzing container with XML config file")
                return self._analyze_xml_config(config_contents=None)
            elif self.container.has_config_txt:
                self.log(u"Analyzing container with TXT config file")
                return self._analyze_txt_config(config_string=None)
            else:
                self.log(u"No configuration file in this container, returning None")
        except (OSError, KeyError, TypeError) as exc:
            self.log_exc(u"An unexpected error occurred while analyzing", exc, True, None)
        return None

    def _analyze_txt_config(self, config_string=None):
        """
        Analyze the given container and return the corresponding job.

        If ``config_string`` is ``None``,
        try reading it from the TXT config file inside the container.

        :param string config_string: the configuration string
        :rtype: :class:`~aeneas.job.Job`
        """
        self.log(u"Analyzing container with TXT config string")

        if config_string is None:
            self.log(u"Analyzing container with TXT config file")
            config_entry = self.container.entry_config_txt
            self.log([u"Found TXT config entry '%s'", config_entry])
            config_dir = os.path.dirname(config_entry)
            self.log([u"Directory of TXT config entry: '%s'", config_dir])
            self.log([u"Reading TXT config entry: '%s'", config_entry])
            config_contents = self.container.read_entry(config_entry)
            self.log(u"Converting config contents to config string")
            config_contents = gf.safe_unicode(config_contents)
            config_string = gf.config_txt_to_string(config_contents)
        else:
            self.log([u"Analyzing container with TXT config string '%s'", config_string])
            config_dir = ""

        self.log(u"Creating the Job object")
        job = Job(config_string)

        self.log(u"Getting entries")
        entries = self.container.entries

        self.log(u"Converting config string into config dict")
        parameters = gf.config_string_to_dict(config_string)

        self.log(u"Calculating the path of the tasks root directory")
        tasks_root_directory = gf.norm_join(
            config_dir,
            parameters[gc.PPN_JOB_IS_HIERARCHY_PREFIX]
        )
        self.log([u"Path of the tasks root directory: '%s'", tasks_root_directory])

        self.log(u"Calculating the path of the sync map root directory")
        sync_map_root_directory = gf.norm_join(
            config_dir,
            parameters[gc.PPN_JOB_OS_HIERARCHY_PREFIX]
        )
        job_os_hierarchy_type = parameters[gc.PPN_JOB_OS_HIERARCHY_TYPE]
        self.log([u"Path of the sync map root directory: '%s'", sync_map_root_directory])

        text_file_relative_path = parameters[gc.PPN_JOB_IS_TEXT_FILE_RELATIVE_PATH]
        self.log([u"Relative path for text file: '%s'", text_file_relative_path])
        text_file_name_regex = re.compile(r"" + parameters[gc.PPN_JOB_IS_TEXT_FILE_NAME_REGEX])
        self.log([u"Regex for text file: '%s'", parameters[gc.PPN_JOB_IS_TEXT_FILE_NAME_REGEX]])
        audio_file_relative_path = parameters[gc.PPN_JOB_IS_AUDIO_FILE_RELATIVE_PATH]
        self.log([u"Relative path for audio file: '%s'", audio_file_relative_path])
        audio_file_name_regex = re.compile(r"" + parameters[gc.PPN_JOB_IS_AUDIO_FILE_NAME_REGEX])
        self.log([u"Regex for audio file: '%s'", parameters[gc.PPN_JOB_IS_AUDIO_FILE_NAME_REGEX]])

        if parameters[gc.PPN_JOB_IS_HIERARCHY_TYPE] == HierarchyType.FLAT:
            self.log(u"Looking for text/audio pairs in flat hierarchy")
            text_files = self._find_files(
                entries,
                tasks_root_directory,
                text_file_relative_path,
                text_file_name_regex
            )
            self.log([u"Found text files: '%s'", text_files])
            audio_files = self._find_files(
                entries,
                tasks_root_directory,
                audio_file_relative_path,
                audio_file_name_regex
            )
            self.log([u"Found audio files: '%s'", audio_files])

            self.log(u"Matching files in flat hierarchy...")
            matched_tasks = self._match_files_flat_hierarchy(
                text_files,
                audio_files
            )
            self.log(u"Matching files in flat hierarchy... done")

            for task_info in matched_tasks:
                self.log([u"Creating task: '%s'", str(task_info)])
                task = self._create_task(
                    task_info,
                    config_string,
                    sync_map_root_directory,
                    job_os_hierarchy_type
                )
                job.add_task(task)

        if parameters[gc.PPN_JOB_IS_HIERARCHY_TYPE] == HierarchyType.PAGED:
            self.log(u"Looking for text/audio pairs in paged hierarchy")
            # find all subdirectories of tasks_root_directory
            # that match gc.PPN_JOB_IS_TASK_DIRECTORY_NAME_REGEX
            matched_directories = self._match_directories(
                entries,
                tasks_root_directory,
                parameters[gc.PPN_JOB_IS_TASK_DIRECTORY_NAME_REGEX]
            )
            for matched_directory in matched_directories:
                # rebuild the full path
                matched_directory_full_path = gf.norm_join(
                    tasks_root_directory,
                    matched_directory
                )
                self.log([u"Looking for text/audio pairs in directory '%s'", matched_directory_full_path])

                # look for text and audio files there
                text_files = self._find_files(
                    entries,
                    matched_directory_full_path,
                    text_file_relative_path,
                    text_file_name_regex
                )
                self.log([u"Found text files: '%s'", text_files])
                audio_files = self._find_files(
                    entries,
                    matched_directory_full_path,
                    audio_file_relative_path,
                    audio_file_name_regex
                )
                self.log([u"Found audio files: '%s'", audio_files])

                # if we have found exactly one text and one audio file,
                # create a Task
                if (len(text_files) == 1) and (len(audio_files) == 1):
                    self.log([u"Exactly one text file and one audio file in '%s'", matched_directory])
                    task_info = [
                        matched_directory,
                        text_files[0],
                        audio_files[0]
                    ]
                    self.log([u"Creating task: '%s'", str(task_info)])
                    task = self._create_task(
                        task_info,
                        config_string,
                        sync_map_root_directory,
                        job_os_hierarchy_type
                    )
                    job.add_task(task)
                elif len(text_files) > 1:
                    self.log([u"More than one text file in '%s'", matched_directory])
                elif len(audio_files) > 1:
                    self.log([u"More than one audio file in '%s'", matched_directory])
                else:
                    self.log([u"No text nor audio file in '%s'", matched_directory])

        return job

    def _analyze_xml_config(self, config_contents=None):
        """
        Analyze the given container and return the corresponding job.

        If ``config_contents`` is ``None``,
        try reading it from the XML config file inside the container.

        :param string config_contents: the contents of the XML config file
        :rtype: :class:`~aeneas.job.Job`
        """
        self.log(u"Analyzing container with XML config string")

        if config_contents is None:
            self.log(u"Analyzing container with XML config file")
            config_entry = self.container.entry_config_xml
            self.log([u"Found XML config entry '%s'", config_entry])
            config_dir = os.path.dirname(config_entry)
            self.log([u"Directory of XML config entry: '%s'", config_dir])
            self.log([u"Reading XML config entry: '%s'", config_entry])
            config_contents = self.container.read_entry(config_entry)
        else:
            self.log(u"Analyzing container with XML config contents")
            config_dir = ""

        self.log(u"Converting config contents into job config dict")
        job_parameters = gf.config_xml_to_dict(
            config_contents,
            result=None,
            parse_job=True
        )
        self.log(u"Converting config contents into tasks config dict")
        tasks_parameters = gf.config_xml_to_dict(
            config_contents,
            result=None,
            parse_job=False
        )

        self.log(u"Calculating the path of the sync map root directory")
        sync_map_root_directory = gf.norm_join(
            config_dir,
            job_parameters[gc.PPN_JOB_OS_HIERARCHY_PREFIX]
        )
        job_os_hierarchy_type = job_parameters[gc.PPN_JOB_OS_HIERARCHY_TYPE]
        self.log([u"Path of the sync map root directory: '%s'", sync_map_root_directory])

        self.log(u"Converting job config dict into job config string")
        config_string = gf.config_dict_to_string(job_parameters)
        job = Job(config_string)

        for task_parameters in tasks_parameters:
            self.log(u"Converting task config dict into task config string")
            config_string = gf.config_dict_to_string(task_parameters)
            self.log([u"Creating task with config string '%s'", config_string])
            try:
                custom_id = task_parameters[gc.PPN_TASK_CUSTOM_ID]
            except KeyError:
                custom_id = ""
            task_info = [
                custom_id,
                gf.norm_join(
                    config_dir,
                    task_parameters[gc.PPN_TASK_IS_TEXT_FILE_XML]
                ),
                gf.norm_join(
                    config_dir,
                    task_parameters[gc.PPN_TASK_IS_AUDIO_FILE_XML]
                )
            ]
            self.log([u"Creating task: '%s'", str(task_info)])
            task = self._create_task(
                task_info,
                config_string,
                sync_map_root_directory,
                job_os_hierarchy_type
            )
            job.add_task(task)

        return job

    def _create_task(
            self,
            task_info,
            config_string,
            sync_map_root_directory,
            job_os_hierarchy_type
    ):
        """
        Create a task object from

        1. the ``task_info`` found analyzing the container entries, and
        2. the given ``config_string``.

        :param list task_info: the task information: ``[prefix, text_path, audio_path]``
        :param string config_string: the configuration string
        :param string sync_map_root_directory: the root directory for the sync map files
        :param job_os_hierarchy_type: type of job output hierarchy
        :type  job_os_hierarchy_type: :class:`~aeneas.hierarchytype.HierarchyType`
        :rtype: :class:`~aeneas.task.Task`
        """
        self.log(u"Converting config string to config dict")
        parameters = gf.config_string_to_dict(config_string)
        self.log(u"Creating task")
        task = Task(config_string, logger=self.logger)
        task.configuration["description"] = "Task %s" % task_info[0]
        self.log([u"Task description: %s", task.configuration["description"]])
        try:
            task.configuration["language"] = parameters[gc.PPN_TASK_LANGUAGE]
            self.log([u"Set language from task: '%s'", task.configuration["language"]])
        except KeyError:
            task.configuration["language"] = parameters[gc.PPN_JOB_LANGUAGE]
            self.log([u"Set language from job: '%s'", task.configuration["language"]])
        custom_id = task_info[0]
        task.configuration["custom_id"] = custom_id
        self.log([u"Task custom_id: %s", task.configuration["custom_id"]])
        task.text_file_path = task_info[1]
        self.log([u"Task text file path: %s", task.text_file_path])
        task.audio_file_path = task_info[2]
        self.log([u"Task audio file path: %s", task.audio_file_path])
        task.sync_map_file_path = self._compute_sync_map_file_path(
            sync_map_root_directory,
            job_os_hierarchy_type,
            custom_id,
            task.configuration["o_name"]
        )
        self.log([u"Task sync map file path: %s", task.sync_map_file_path])

        self.log(u"Replacing placeholder in os_file_smil_audio_ref")
        task.configuration["o_smil_audio_ref"] = self._replace_placeholder(
            task.configuration["o_smil_audio_ref"],
            custom_id
        )
        self.log(u"Replacing placeholder in os_file_smil_page_ref")
        task.configuration["o_smil_page_ref"] = self._replace_placeholder(
            task.configuration["o_smil_page_ref"],
            custom_id
        )
        self.log(u"Returning task")
        return task

    def _replace_placeholder(self, string, custom_id):
        """
        Replace the prefix placeholder
        :class:`~aeneas.globalconstants.PPV_OS_TASK_PREFIX`
        with ``custom_id`` and return the resulting string.

        :rtype: string
        """
        if string is None:
            return None
        self.log([u"Replacing '%s' with '%s' in '%s'", gc.PPV_OS_TASK_PREFIX, custom_id, string])
        return string.replace(gc.PPV_OS_TASK_PREFIX, custom_id)

    def _compute_sync_map_file_path(
            self,
            root,
            hierarchy_type,
            custom_id,
            file_name
    ):
        """
        Compute the sync map file path inside the output container.

        :param string root: the root of the sync map files inside the container
        :param job_os_hierarchy_type: type of job output hierarchy
        :type  job_os_hierarchy_type: :class:`~aeneas.hierarchytype.HierarchyType`
        :param string custom_id: the task custom id (flat) or
                                 page directory name (paged)
        :param string file_name: the output file name for the sync map
        :rtype: string
        """
        prefix = root
        if hierarchy_type == HierarchyType.PAGED:
            prefix = gf.norm_join(prefix, custom_id)
        file_name_joined = gf.norm_join(prefix, file_name)
        return self._replace_placeholder(file_name_joined, custom_id)

    def _find_files(self, entries, root, relative_path, file_name_regex):
        """
        Return the elements in entries that

        1. are in ``root/relative_path``, and
        2. match ``file_name_regex``.

        :param list entries: the list of entries (file paths) in the container
        :param string root: the root directory of the container
        :param string relative_path: the relative path in which we must search
        :param regex file_name_regex: the regex matching the desired file names
        :rtype: list of strings (path)
        """
        self.log([u"Finding files within root: '%s'", root])
        target = root
        if relative_path is not None:
            self.log([u"Joining relative path: '%s'", relative_path])
            target = gf.norm_join(root, relative_path)
        self.log([u"Finding files within target: '%s'", target])
        files = []
        target_len = len(target)
        for entry in entries:
            if entry.startswith(target):
                self.log([u"Examining entry: '%s'", entry])
                entry_suffix = entry[target_len + 1:]
                self.log([u"Examining entry suffix: '%s'", entry_suffix])
                if re.search(file_name_regex, entry_suffix) is not None:
                    self.log([u"Match: '%s'", entry])
                    files.append(entry)
                else:
                    self.log([u"No match: '%s'", entry])
        return sorted(files)

    def _match_files_flat_hierarchy(self, text_files, audio_files):
        """
        Match audio and text files in flat hierarchies.

        Two files match if their names,
        once removed the file extension,
        are the same.

        Examples: ::

            foo/text/a.txt foo/audio/a.mp3 => match: ["a", "foo/text/a.txt", "foo/audio/a.mp3"]
            foo/text/a.txt foo/audio/b.mp3 => no match
            foo/res/c.txt  foo/res/c.mp3   => match: ["c", "foo/res/c.txt", "foo/res/c.mp3"]
            foo/res/d.txt  foo/res/e.mp3   => no match

        :param list text_files: the entries corresponding to text files
        :param list audio_files: the entries corresponding to audio files
        :rtype: list of lists (see above)
        """
        self.log(u"Matching files in flat hierarchy")
        self.log([u"Text files: '%s'", text_files])
        self.log([u"Audio files: '%s'", audio_files])
        d_text = {}
        d_audio = {}
        for text_file in text_files:
            text_file_no_ext = gf.file_name_without_extension(text_file)
            d_text[text_file_no_ext] = text_file
            self.log([u"Added text file '%s' to key '%s'", text_file, text_file_no_ext])
        for audio_file in audio_files:
            audio_file_no_ext = gf.file_name_without_extension(audio_file)
            d_audio[audio_file_no_ext] = audio_file
            self.log([u"Added audio file '%s' to key '%s'", audio_file, audio_file_no_ext])
        tasks = []
        for key in d_text.keys():
            self.log([u"Examining text key '%s'", key])
            if key in d_audio:
                self.log([u"Key '%s' is also in audio", key])
                tasks.append([key, d_text[key], d_audio[key]])
                self.log([u"Added pair ('%s', '%s')", d_text[key], d_audio[key]])
        return tasks

    def _match_directories(self, entries, root, regex_string):
        """
        Match directory names in paged hierarchies.

        Example: ::

            root = /foo/bar
            regex_string = [0-9]+

            /foo/bar/
                     1/
                       bar
                       baz
                     2/
                       bar
                     3/
                       foo

            => ["/foo/bar/1", "/foo/bar/2", "/foo/bar/3"]

        :param list entries: the list of entries (paths) of a container
        :param string root: the root directory to search within
        :param string regex_string: regex string to match directory names
        :rtype: list of matched directories
        """
        self.log(u"Matching directory names in paged hierarchy")
        self.log([u"Matching within '%s'", root])
        self.log([u"Matching regex '%s'", regex_string])
        regex = re.compile(r"" + regex_string)
        directories = set()
        root_len = len(root)
        for entry in entries:
            # look only inside root dir
            if entry.startswith(root):
                self.log([u"Examining '%s'", entry])
                # remove common prefix root/
                entry = entry[root_len + 1:]
                # split path
                entry_splitted = entry.split(os.sep)
                # match regex
                if ((len(entry_splitted) >= 2) and
                        (re.match(regex, entry_splitted[0]) is not None)):
                    directories.add(entry_splitted[0])
                    self.log([u"Match: '%s'", entry_splitted[0]])
                else:
                    self.log([u"No match: '%s'", entry])
        return sorted(directories)
