# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
import sgtk
from sgtk import TankError
import NatronGui


__author__ = "Diego Garcia Huerta"
__email__ = "diegogh2000@gmail.com"


HookBaseClass = sgtk.get_hook_baseclass()


class FrameOperation(HookBaseClass):
    """
    Hook called to perform a frame operation with the 
    current scene
    """

    def execute(self, operation, in_frame=None, out_frame=None, **kwargs):
        """
        Main hook entry point

        :operation: String
                    Frame operation to perform

        :in_frame: int
                    in_frame for the current context (e.g. the current shot, 
                                                      current asset etc)

        :out_frame: int
                    out_frame for the current context (e.g. the current shot, 
                                                      current asset etc)

        :returns:   Depends on operation:
                    'set_frame_range' - Returns if the operation was succesfull
                    'get_frame_range' - Returns the frame range in the form
                                        (in_frame, out_frame)
        """
        natron_app = NatronGui.natron.getActiveInstance()

        if operation == "get_frame_range":
            current_in = natron_app.timelineGetLeftBound()
            current_out = natron_app.timelineGetRightBound()
            return (current_in, current_out)
        elif operation == "set_frame_range":
            natron_app.getProjectParam('frameRange').set(in_frame, out_frame)
            return True
