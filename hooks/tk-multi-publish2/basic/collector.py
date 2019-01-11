# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import glob
import os
import sgtk

import NatronGui

HookBaseClass = sgtk.get_hook_baseclass()


class NatronSessionCollector(HookBaseClass):
    """
    Collector that operates on the natron session. Should inherit from the basic
    collector hook.
    """

    @property
    def settings(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """

        # grab any base class settings
        collector_settings = super(NatronSessionCollector, self).settings or {}

        # settings specific to this collector
        natron_session_settings = {
            "Work Template": {
                "type": "template",
                "default": None,
                "description": "Template path for artist work files. Should "
                               "correspond to a template defined in "
                               "templates.yml. If configured, is made available"
                               "to publish plugins via the collected item's "
                               "properties. ",
            },
        }

        # update the base settings with these settings
        collector_settings.update(natron_session_settings)

        return collector_settings

    def process_current_session(self, settings, parent_item):
        """
        Analyzes the current session open in Natron and parents a subtree of
        items under the parent_item passed in.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance

        """

        # create an item representing the current natron session
        item = self.collect_current_natron_session(settings, parent_item)

    def collect_current_natron_session(self, settings, parent_item):
        """
        Creates an item that represents the current natron session.

        :param parent_item: Parent Item instance

        :returns: Item of type natron.session
        """

        publisher = self.parent

        # get the path to the current file
        path = _session_path()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Natron Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "natron.session",
            "Natron Session",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "natron.png"
        )
        session_item.set_icon_from_path(icon_path)

        # if a work template is defined, add it to the item properties so
        # that it can be used by attached publish plugins
        work_template_setting = settings.get("Work Template")
        if work_template_setting:

            work_template = publisher.engine.get_template_by_name(
                work_template_setting.value)

            # store the template on the item for use by publish plugins. we
            # can't evaluate the fields here because there's no guarantee the
            # current session path won't change once the item has been created.
            # the attached publish plugins will need to resolve the fields at
            # execution time.
            session_item.properties["work_template"] = work_template
            session_item.properties["publish_type"] = "Natron Project File"
            self.logger.debug("Work template defined for Natron collection.")

        self.logger.info("Collected current Natron scene")

        return session_item

def _session_path():
    """
    Return the path to the current session
    :return:
    """
    natron_app = NatronGui.natron.getActiveInstance()

    project_name = natron_app.getProjectParam('projectName').getValue()
    project_path = natron_app.getProjectParam('projectPath').getValue()
    path = os.path.join(project_path, project_name)

    if isinstance(path, unicode):
        path = path.encode("utf-8")

    return path


