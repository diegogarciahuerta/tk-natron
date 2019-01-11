# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""A Natron engine for Tank.
https://en.wikipedia.org/wiki/Natron_(software)
"""

import os
import sys
import time
import inspect
import logging
import traceback

from functools import wraps

import tank
from tank.log import LogManager
from tank.platform import Engine
from tank.platform.constants import SHOTGUN_ENGINE_NAME

import NatronEngine
from NatronEngine import natron


__author__ = "Diego Garcia Huerta"
__email__ = "diegogh2000@gmail.com"


# env variable that control if to show the compatibility warning dialog
# when Natron software version is above the tested one.
SHOW_COMP_DLG = "SGTK_COMPATIBILITY_DIALOG_SHOWN"

# this is a place to put our scene callbacks
if not hasattr(natron, "shotgun"):
    natron.shotgun = lambda: None


# scene related callbacks
def on_afterProjectCreated(app):
    if natron.shotgun.automatic_context_switch:
        refresh_engine(app, natron.shotgun._engine_instance,
                       None, menu_name=natron.shotgun._menu_name)


def on_afterProjectLoad(app):
    if natron.shotgun.automatic_context_switch:
        refresh_engine(app, natron.shotgun._engine_instance,
                       None, menu_name=natron.shotgun._menu_name)


# register the scene callbacks
natron.shotgun.afterProjectCreated = on_afterProjectCreated
natron.shotgun.afterProjectLoad = on_afterProjectLoad
natron.setOnProjectCreatedCallback(
    "NatronEngine.natron.shotgun.afterProjectCreated")
natron.setOnProjectLoadedCallback(
    "NatronEngine.natron.shotgun.afterProjectLoad")


# logging functionality
def show_error(msg):
    batch_mode = natron.isBackground()
    if not batch_mode:
        NatronGui.natron.errorDialog("Shotgun Error | Natron engine", msg)
    else:
        display_error(msg)


def show_warning(msg):
    batch_mode = natron.isBackground()
    if not batch_mode:
        NatronGui.natron.warningDialog("Shotgun warning | Natron engine", msg)
    else:
        display_warning(msg)


def show_info(msg):
    batch_mode = natron.isBackground()
    if not batch_mode:
        NatronGui.natron.informationDialog("Shotgun Info | Natron engine", msg)
    else:
        display_info(msg)


def display_error(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgun Error | Natron engine | %s " % (t, msg))


def display_warning(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgun Warning | Natron engine | %s " % (t, msg))


def display_info(msg):
    t = time.asctime(time.localtime())
    print("%s - Shotgun Info | Natron engine | %s " % (t, msg))


def display_debug(msg):
    if os.environ.get("TK_DEBUG") == "1":
        t = time.asctime(time.localtime())
        print("%s - Shotgun Debug | Natron engine | %s " % (t, msg))


# methods to support the state when the engine cannot start up
# for example if a non-tank file is loaded in natron we load the project
# context if exists, so we give a chance to the user to at least
# do the basics operations.

def refresh_engine(natron_app, engine_name, prev_context, menu_name):
    """
    refresh the current engine
    """
    current_engine = tank.platform.current_engine()

    if not current_engine:
        # If we don't have an engine for some reason then we don't have
        # anything to do.
        sys.stdout.write("refresh_engine | no engine!\n")
        return

    project_name = natron_app.getProjectParam('projectName').getValue()
    project_path = natron_app.getProjectParam('projectPath').getValue()
    scene_name = os.path.join(project_path, project_name)

    # This is a File->New call, so we just leave the engine in the current
    # context and move on.
    if scene_name == "Untitled.ntp":
        if prev_context and prev_context != current_engine.context:
            current_engine.change_context(prev_context)

        # shotgun menu may have been removed, so add it back in if its not
        # already there.
        current_engine.create_shotgun_menu()
        return

    # determine the tk instance and ctx to use:
    tk = current_engine.sgtk

    # loading a scene file
    new_path = os.path.abspath(scene_name)

    # this file could be in another project altogether, so create a new
    # API instance.
    try:
        # and construct the new context for this path:
        tk = tank.tank_from_path(new_path)
        ctx = tk.context_from_path(new_path, prev_context)
    except tank.TankError, e:
        try:
            # could not detect context from path, will use the project context
            # for menus if it exists
            ctx = current_engine.sgtk.context_from_entity_dictionary(
                current_engine.context.project)
            message = ("Shotgun Natron Engine could not detect the context\n"
                       "the project loaded. Shotgun menus will be reset \n"
                       "to the project '%s' "
                       "context."
                       "\n" % current_engine.context.project.get('name'))
            display_warning(message)

        except tank.TankError, e:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            message = ""
            message += "Shotgun Natron Engine cannot be started:.\n"
            message += "Please contact support@shotgunsoftware.com\n\n"
            message += "Exception: %s - %s\n" % (exc_type, exc_value)
            message += "Traceback (most recent call last):\n"
            message += "\n".join(traceback.format_tb(exc_traceback))

            # disabled menu, could not get project context
            current_engine.create_shotgun_menu(disabled=True)
            display_error(message)
            return

    # shotgun menu may have been removed,
    # so add it back in if its not already there.
    current_engine.create_shotgun_menu()

    if ctx != tank.platform.current_engine().context:
        current_engine.change_context(ctx)


class NatronEngine(Engine):
    """
    Toolkit engine for Natron.
    """

    def __get_platform_resource_path(self, filename):
        """
        Returns the full path to the given platform resource file or folder.
        Resources reside in the core/platform/qt folder.
        :return: full path
        """
        tank_platform_folder = os.path.abspath(inspect.getfile(tank.platform))
        return os.path.join(tank_platform_folder, "qt", filename)

    def __toggle_debug_logging(self):
        """
        Toggles global debug logging on and off in the log manager.
        This will affect all logging across all of toolkit.
        """
        # flip debug logging
        LogManager().global_debug = not LogManager().global_debug

    def __open_log_folder(self):
        """
        Opens the file system folder where log files are being stored.
        """
        self.log_info("Log folder is located in '%s'" %
                      LogManager().log_folder)

        if self.has_ui:
            # only import QT if we have a UI
            from sgtk.platform.qt import QtGui, QtCore
            url = QtCore.QUrl.fromLocalFile(
                LogManager().log_folder
            )
            status = QtGui.QDesktopServices.openUrl(url)
            if not status:
                self._engine.log_error("Failed to open folder!")

    def __register_open_log_folder_command(self):
        """
        # add a 'open log folder' command to the engine's context menu
        # note: we make an exception for the shotgun engine which is a
        # special case.
        """
        if self.name != SHOTGUN_ENGINE_NAME:
            icon_path = self.__get_platform_resource_path("folder_256.png")

            self.register_command(
                "Open Log Folder",
                self.__open_log_folder,
                {
                    "short_name": "open_log_folder",
                    "icon": icon_path,
                    "description": ("Opens the folder where log files are "
                                    "being stored."),
                    "type": "context_menu"
                }
            )

    def __register_reload_command(self):
        """
        Registers a "Reload and Restart" command with the engine if any
        running apps are registered via a dev descriptor.
        """
        from tank.platform import restart
        self.register_command(
            "Reload and Restart",
            restart,
            {"short_name": "restart",
             "icon": self.__get_platform_resource_path("reload_256.png"),
             "type": "context_menu"}
        )

    @property
    def context_change_allowed(self):
        """
        Whether the engine allows a context change without the need for a restart.
        """
        return True

    @property
    def host_info(self):
        """
        :returns: A dictionary with information about the application hosting this engine.

        The returned dictionary is of the following form on success:

            {
                "name": "Natron",
                "version": "2.3.14",
            }

        The returned dictionary is of following form on an error preventing
        the version identification.

            {
                "name": "Natron",
                "version: "unknown"
            }
        """

        host_info = {"name": "Natron", "version": "unknown"}
        try:
            natron_ver = natron.getNatronVersionString()
            host_info["version"] = natron_ver
        except:
            # Fallback to 'Natron' initialized above
            pass
        return host_info

    def _install_cacert_file(self):
        """
        Unfortunately, it seems that the SSL certificate does not work
        with the Natron urlib2 library so we need to install it from
        the shotgun_apiv3, otherwise, any upload/download operations
        to shotgun will fail, ie. retrieving/uploading thumbnails.
        """

        self.ssl_cert_file = os.environ.get("SSL_CERT_FILE")

        try:
            import inspect
            import tank_vendor.shotgun_api3.lib.httplib2 as sapi3_httplib2
            httplib2_file = inspect.getfile(sapi3_httplib2)
            httplib2_dir = os.path.dirname(httplib2_file)
            cacerts_file = os.path.join(httplib2_dir, "cacerts.txt")
            if os.path.exists(cacerts_file):
                os.environ["SSL_CERT_FILE"] = cacerts_file

        except Exception, exception:
            traceback.print_exc()
            self.logger.warning("Could not install Shotgun cacert.txt"
                                " certificate due to the following exception:"
                                " %s", exception)

    def _restore_cacert_file(self):
        if self.ssl_cert_file is None:
            del os.environ["SSL_CERT_FILE"]
        else:
            os.environ["SSL_CERT_FILE"] = ssl_cert_file

    def pre_app_init(self):
        """
        Runs after the engine is set up but before any apps have been
        initialized.
        """
        # unicode characters returned by the shotgun api need to be converted
        # to display correctly in all of the app windows
        from tank.platform.qt import QtCore

        # tell QT to interpret C strings as utf-8
        utf8 = QtCore.QTextCodec.codecForName("utf-8")
        QtCore.QTextCodec.setCodecForCStrings(utf8)
        self.logger.debug("set utf-8 codec for widget text")

        self.logger.debug("Installing certificate file from shotgun_api3")
        self._install_cacert_file()

    def init_engine(self):
        """
        Initializes the Natron engine.
        """
        self.logger.debug("%s: Initializing...", self)

        # check that we are running an ok version of natron
        current_os = sys.platform
        if current_os not in ["mac", "win32", "linux64"]:
            raise tank.TankError("The current platform is not supported!"
                                 " Supported platforms "
                                 "are Mac, Linux 64 and Windows 64.")

        natron_build_version = natron.getNatronVersionString()
        natron_ver = float(".".join(natron_build_version.split(".")[:2]))

        if natron_ver < 2.3:
            msg = ("Shotgun integration is not compatible with Natron versions"
                   " older than 2.3.0")
            raise tank.TankError(msg)

        if natron_ver > 2.3:
            # show a warning that this version of Natron isn't yet fully tested
            # with Shotgun:
            msg = ("The Shotgun Pipeline Toolkit has not yet been fully "
                   "tested with Natron %s.  "
                   "You can continue to use Toolkit but you may experience "
                   "bugs or instability."
                   "\n\n"
                   % (natron_ver))

            # determine if we should show the compatibility warning dialog:
            show_warning_dlg = self.has_ui and SHOW_COMP_DLG not in os.environ

            if show_warning_dlg:
                # make sure we only show it once per session
                os.environ[SHOW_COMP_DLG] = "1"

                # split off the major version number - accomodate complex
                # version strings and decimals:
                major_version_number_str = natron_build_version.split(".")[0]
                if (major_version_number_str and
                        major_version_number_str.isdigit()):
                    # check against the compatibility_dialog_min_version
                    # setting
                    min_ver = self.get_setting(
                        "compatibility_dialog_min_version")
                    if int(major_version_number_str) < min_ver:
                        show_warning_dlg = False

            if show_warning_dlg:
                # Note, title is padded to try to ensure dialog isn't insanely
                # narrow!
                show_info(msg)

            # always log the warning to the script editor:
            self.logger.warning(msg)

            # In the case of Windows, we have the possility of locking up if
            # we allow the PySide shim to import QtWebEngineWidgets.
            # We can stop that happening here by setting the following
            # environment variable.

            if current_os.startswith("win"):
                self.logger.debug(
                    "Natron on Windows can deadlock if QtWebEngineWidgets "
                    "is imported. Setting "
                    "SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT=1..."
                )
                os.environ["SHOTGUN_SKIP_QTWEBENGINEWIDGETS_IMPORT"] = "1"

        # add qt paths and dlls
        self._init_pyside()

        # default menu name is Shotgun but this can be overriden
        # in the configuration to be Sgtk in case of conflicts
        self._menu_name = "Shotgun"
        if self.get_setting("use_sgtk_as_menu_name", False):
            self._menu_name = "Sgtk"

        # set values for callbacks as they are out of this class
        natron.shotgun._engine_instance = self.instance_name
        natron.shotgun._menu_name = self._menu_name
        natron.shotgun.automatic_context_switch = self.get_setting(
            "automatic_context_switch", True)

    def create_shotgun_menu(self, disabled=False):
        """
        Creates the main shotgun menu in natron.
        Note that this only creates the menu, not the child actions
        :return: bool
        """

        # only create the shotgun menu if not in batch mode and menu doesn't
        # already exist
        if self.has_ui:
            # create our menu handler
            tk_natron = self.import_module("tk_natron")
            self._menu_generator = tk_natron.MenuGenerator(
                self, self._menu_name)
            self._menu_generator.create_menu(disabled=disabled)
            return True

        return False

    def _initialise_qapplication(self):
        """
        Ensure the QApplication is initialized
        """
        from sgtk.platform.qt import QtGui

        qt_app = QtGui.QApplication.instance()
        if qt_app is None:
            self.log_debug("Initialising main QApplication...")
            qt_app = QtGui.QApplication([])
            qt_app.setWindowIcon(QtGui.QIcon(self.icon_256))
            qt_app.setQuitOnLastWindowClosed(False)

            # set up the dark style
            self._initialize_dark_look_and_feel()

        # pyqt_natron.exec_(qt_app)

    def post_app_init(self):
        """
        Called when all apps have initialized
        """
        self._initialise_qapplication()

        # for some readon this engine command get's lost so we add it back
        self.__register_reload_command()
        self.create_shotgun_menu()

        # Run a series of app instance commands at startup.
        self._run_app_instance_commands()

    def post_context_change(self, old_context, new_context):
        """
        Runs after a context change. The Natron event watching will be stopped
        and new callbacks registered containing the new context information.

        :param old_context: The context being changed away from.
        :param new_context: The new context being changed to.
        """

        # restore the open log folder, it get's removed whenever the first time
        # a context is changed
        self.__register_open_log_folder_command()
        self.__register_reload_command()

        if self.get_setting("automatic_context_switch", True):
            natron.shotgun._engine_instance = self.instance_name
            natron.shotgun._menu_name = self._menu_name
            natron.shotgun._new_context = new_context

            self.logger.debug(
                "Registered new open and save callbacks before "
                "changing context."
            )

            # finally create the menu with the new context if needed
            if old_context != new_context:
                self.create_shotgun_menu()

    def _run_app_instance_commands(self):
        """
        Runs the series of app instance commands listed in the 
        'run_at_startup' setting of the environment configuration yaml file.
        """

        # Build a dictionary mapping app instance names to dictionaries of
        # commands they registered with the engine.
        app_instance_commands = {}
        for (cmd_name, value) in self.commands.iteritems():
            app_instance = value["properties"].get("app")
            if app_instance:
                # Add entry 'command name: command function' to the command
                # dictionary of this app instance.
                cmd_dict = app_instance_commands.setdefault(
                    app_instance.instance_name, {})
                cmd_dict[cmd_name] = value["callback"]

        # Run the series of app instance commands listed in the
        # 'run_at_startup' setting.
        for app_setting_dict in self.get_setting("run_at_startup", []):
            app_instance_name = app_setting_dict["app_instance"]

            # Menu name of the command to run or '' to run all commands of the
            # given app instance.
            setting_cmd_name = app_setting_dict["name"]

            # Retrieve the command dictionary of the given app instance.
            cmd_dict = app_instance_commands.get(app_instance_name)

            if cmd_dict is None:
                self.logger.warning(
                    "%s configuration setting 'run_at_startup' requests app"
                    " '%s' that is not installed.",
                    self.name, app_instance_name)
            else:
                if not setting_cmd_name:
                    # Run all commands of the given app instance.
                    for (cmd_name, command_function) in cmd_dict.iteritems():
                        msg = ("%s startup running app '%s' command '%s'.",
                               self.name, app_instance_name, cmd_name)
                        self.logger.debug(msg)

                        command_function()
                else:
                    # Run the command whose name is listed in the
                    # 'run_at_startup' setting.
                    command_function = cmd_dict.get(setting_cmd_name)
                    if command_function:
                        msg = ("%s startup running app '%s' command '%s'.",
                               self.name, app_instance_name, setting_cmd_name)
                        self.logger.debug(msg)

                        command_function()
                    else:
                        known_commands = ', '.join(
                            "'%s'" % name for name in cmd_dict)
                        self.logger.warning(
                            "%s configuration setting 'run_at_startup' "
                            "requests app '%s' unknown command '%s'. "
                            "Known commands: %s",
                            self.name, app_instance_name,
                            setting_cmd_name, known_commands)

    def destroy_engine(self):
        """
        Remove the callback scene events.
        TODO: restore and preserve the existing ones.
        """
        self.logger.debug("%s: Destroying...", self)

        if self.get_setting("automatic_context_switch", True):
            natron.setOnProjectCreatedCallback("")
            natron.setOnProjectLoadedCallback("")

        # fineally restore the cacert certificate we replaced if there was one
        # in the first place
        self._restore_cacert_file()

    def _init_pyside(self):
        """
        Handles the pyside init
        """

        # import PySide first or we are in trouble
        try:
            from PySide import QtGui
        except Exception, e:
            traceback.print_exc()
            self.logger.error("PySide could not be imported! Apps using pyside"
                              " will not operate correctly!"
                              "Error reported: %s", e)

    def _get_dialog_parent(self):
        """
        Get the QWidget parent for all dialogs created through
        show_dialog & show_modal.
        """

        # Unfornately there is no easy way to retrieve the QMainWindow from
        # Natron. Following widgets ascendants return QWidget types which
        # cannot be guaranteed to be of QMainWindow class type. Tested but
        # did not work proeprly.
        return None

    @property
    def has_ui(self):
        """
        Detect and return if natron is running in batch mode
        """
        batch_mode = natron.isBackground()
        return not batch_mode

    def _emit_log_message(self, handler, record):
        """
        Called by the engine to log messages in Natron script editor.
        All log messages from the toolkit logging namespace will be passed to
        this method.

        :param handler: Log handler that this message was dispatched from.
                        Its default format is "[levelname basename] message".
        :type handler: :class:`~python.logging.LogHandler`
        :param record: Standard python logging record.
        :type record: :class:`~python.logging.LogRecord`
        """
        # Give a standard format to the message:
        #     Shotgun <basename>: <message>
        # where "basename" is the leaf part of the logging record name,
        # for example "tk-multi-shotgunpanel" or "qt_importer".
        if record.levelno < logging.INFO:
            formatter = logging.Formatter(
                "Debug: Shotgun %(basename)s: %(message)s")
        else:
            formatter = logging.Formatter("Shotgun %(basename)s: %(message)s")

        msg = formatter.format(record)

        # Select Natron display function to use according to the logging
        # record level.
        if record.levelno >= logging.ERROR:
            fct = display_error
        elif record.levelno >= logging.WARNING:
            fct = display_warning
        elif record.levelno >= logging.INFO:
            fct = display_info
        else:
            fct = display_debug

        # Display the message in Natron script editor in a thread safe manner.
        self.async_execute_in_main_thread(fct, msg)

    def close_windows(self):
        """
        Closes the various windows (dialogs, panels, etc.) opened by the
        engine.
        """

        # Make a copy of the list of Tank dialogs that have been created by the
        # engine and are still opened since the original list will be updated
        # when each dialog is closed.
        opened_dialog_list = self.created_qt_dialogs[:]

        # Loop through the list of opened Tank dialogs.
        for dialog in opened_dialog_list:
            dialog_window_title = dialog.windowTitle()
            try:
                # Close the dialog and let its close callback remove it from
                # the original dialog list.
                self.logger.debug("Closing dialog %s.", dialog_window_title)
                dialog.close()
            except Exception, exception:
                traceback.print_exc()
                self.logger.error("Cannot close dialog %s: %s",
                                  dialog_window_title, exception)
