import logging
import os

from typing import List

from peek_platform.frontend.FrontendBuilderABC import FrontendBuilderABC
from peek_platform.util.PtyUtil import PtyOutParser, spawnPty, logSpawnException

logger = logging.getLogger(__name__)


class WebBuilder(FrontendBuilderABC):
    def __init__(self, frontendProjectDir: str, platformService: str,
                 jsonCfg, loadedPlugins: List):
        FrontendBuilderABC.__init__(self, frontendProjectDir, platformService,
                                    jsonCfg, loadedPlugins)

    def build(self) -> None:
        if not self._jsonCfg.feWebBuildPrepareEnabled:
            logger.info("SKIPPING, Web build prepare is disabled in config")
            return

        self._dirSyncMap = list()

        feBuildDir = os.path.join(self._frontendProjectDir, 'build-web')
        feSrcAppDir = os.path.join(self._frontendProjectDir, 'src', 'app')

        feBuildSrcDir = os.path.join(feBuildDir, 'src')
        feBuildAssetsDir = os.path.join(feBuildDir, 'src', 'assets')

        feNodeModulesDir = os.path.join(feBuildDir, 'node_modules')

        fePluginModulesDir = os.path.join(feNodeModulesDir,
                                          '@' + self._platformService)

        pluginDetails = self._loadPluginConfigs()

        ## --------------------
        # Check if node_modules exists

        if not os.path.exists(os.path.join(feBuildDir, 'node_modules')):
            raise NotADirectoryError("node_modules doesn't exist, ensure you've run "
                                     "`npm install` in dir %s" % feBuildDir)

        ## --------------------
        # Prepare the common frontend application

        self.fileSync.addSyncMapping(feSrcAppDir, os.path.join(feBuildSrcDir, 'app'))

        ## --------------------
        # Prepare the home and title bar configuration for the plugins
        self._writePluginHomeLinks(feBuildSrcDir, pluginDetails)
        self._writePluginTitleBarLinks(feBuildSrcDir, pluginDetails)

        ## --------------------
        # Prepare the plugin lazy loaded part of the application
        self._writePluginRouteLazyLoads(feBuildSrcDir, pluginDetails)
        self._syncPluginFiles(feBuildSrcDir, pluginDetails, "angularFrontendAppDir")

        ## --------------------
        # Prepare the plugin assets
        self._syncPluginFiles(feBuildAssetsDir, pluginDetails, "angularFrontendAssetsDir")

        ## --------------------
        # Prepare the shared / global parts of the plugins

        self._writePluginRootModules(feBuildSrcDir, pluginDetails, self._platformService)
        self._writePluginRootServices(feBuildSrcDir, pluginDetails, self._platformService)

        # Link the shared code, this allows plugins
        # * to import code from each other.
        # * provide global services.
        self._syncPluginFiles(fePluginModulesDir, pluginDetails,
                              "angularFrontendModuleDir")

        # Lastly, Allow the clients to override any frontend files they wish.
        self.fileSync.addSyncMapping(self._jsonCfg.feFrontendCustomisationsDir,
                                     feBuildSrcDir,
                                     parentMustExist=True,
                                     deleteExtraDstFiles=False)

        self.fileSync.syncFiles()

        if self._jsonCfg.feSyncFilesForDebugEnabled:
            logger.info("Starting frontend development file sync")
            self.fileSync.startFileSyncWatcher()

        if self._jsonCfg.feWebBuildEnabled:
            logger.info("Starting frontend web build")
            self._compileFrontend(feBuildDir)

    def _syncFileHook(self, fileName: str, contents: bytes) -> bytes:
        return contents

    def _compileFrontend(self, feBuildDir: str) -> None:
        """ Compile the frontend

        this runs `ng build`

        We need to use a pty otherwise webpack doesn't run.

        """

        hashFileName = os.path.join(feBuildDir, ".lastHash")

        if not self._recompileRequiredCheck(feBuildDir, hashFileName):
            logger.info("Frondend has not changed, recompile not required.")
            return

        logger.info("Rebuilding frontend distribution")

        try:
            parser = PtyOutParser(loggingStartMarker="Hash: ")
            spawnPty("cd %s && ng build" % feBuildDir, parser)
            logger.info("Frontend distribution rebuild complete.")

        except Exception as e:
            logSpawnException(e)
            if os.path.exists(hashFileName):
                os.remove(hashFileName)

            # Update the detail of the exception and raise it
            e.message = "The angular frontend failed to build."
            raise