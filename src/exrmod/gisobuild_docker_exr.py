# -----------------------------------------------------------------------------

""" Launch Gisobuild in a container.

Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

        https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""

__all__ = (
    "system_resource_prep",
    "setup_copy_out_directory",
    "copy_artefacts",
)

import os
import logging
import sys
import re
import tempfile
from utils import gisoutils
from utils import gisoglobals as gglobals
import pathlib
import argparse
import shutil


logger = logging.getLogger('gisobuild')
_CTR_OUT_DIR = gglobals.CTR_OUT_DIR
_CTR_LOG_DIR = gglobals.CTR_LOG_DIR

def system_resource_prep (args):
    import tempfile
    import shutil

    tempdir = tempfile.mkdtemp (prefix = os.path.join(args.out_directory, ""))
    cliConfig_file = os.path.join (tempdir, "cliConfig.yaml")
    
    args_dict = args.__dict__.copy()
    args_dict ["cli_yaml"] = None
    args_dict ["docker"] = False
    args_dict ["clean"] = False
    args_dict ["in_docker"] = True
    args_dict["out_directory"] = str(_CTR_OUT_DIR)
    
    ''' Copy the giso config, ztp.ini and script to temp staging. '''
    if args.xrconfig:
        shutil.copy (args.xrconfig, tempdir)
        args_dict ["xrconfig"] = os.path.join (tempdir, os.path.basename(args.xrconfig))
        
    if args.ztp_ini:
        shutil.copy (args.ztp_ini, tempdir)
        args_dict ["ztp_ini"] = os.path.join (tempdir, os.path.basename(args.ztp_ini))
        
    if args.script:
        shutil.copy (args.script, tempdir)
        args_dict ["script"] = os.path.join (tempdir, os.path.basename(args.script))
    
    ''' Make necessary changes to yaml file to be passed '''
    gisoutils.dump_yaml_giso_arguments (cliConfig_file, args_dict)
    
    return cliConfig_file
    
def setup_copy_out_directory (args: argparse.Namespace) -> None:
    '''
    Check that copy and output directories are set accordingly.

    :param args
        The arguments provided to the unified giso build script

    '''
    assert args.out_directory is not None

def copy_artefacts (
    src_dir: pathlib.Path,
    log_dir: pathlib.Path,
    out_dir: pathlib.Path,
    copy_dir = None,
) -> None:
    """
    Copy build artefacts from container to specified output directory and copy
    directory

    :param src_dir:
        Directory where built artefacts are staged.

    :param log_dir:
        Log directory.

    :param out_dir:
        Specified output directory

    """
    assert out_dir is not None
    src_log_dir = src_dir / _CTR_LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    import re
    re_list = [".*.txt", ".*-golden.*"]
    artifact_reg = re.compile( '|'.join( re_list) )
    tmp_artifact_dir = src_dir
    for item in tmp_artifact_dir.iterdir():
        if artifact_reg.match (item.name):
            shutil.copy2(item, out_dir)

    logger.info (f"Build artefacts copied to {out_dir}")

    for item in src_log_dir.iterdir():
        if re.match(r".*\.log(\.\d+)?", item.name):
            shutil.copy2 (item, log_dir)

    logger.info (f"Logs copied to {log_dir}")

    return

def create_tpa_repo(cli_args: argparse.Namespace) -> tempfile.TemporaryDirectory:
    tpa_smu_found = False
    if cli_args.pkglist:
        for pkg in cli_args.pkglist:
            if pkg.startswith ("owner-") or pkg.startswith ("partner-"):
                tpa_smu_found = True
                break
    if not tpa_smu_found:
        return None
    try:
        tpa_staging = tempfile.TemporaryDirectory(
            prefix= "TPA_REPO-", dir= cli_args.out_directory
        )
        logger.error("TPA REPO: %s" % (tpa_staging.name))
        for repo in cli_args.repo:
            repo = os.path.normpath(repo)
            ( _, _, files) = tuple(os.walk(repo))[0]
            for file in files:
                file_name = file
                if (
                    re.search(r"^owner-\S*\.rpm",  file_name) or
                    re.search(r"^partner-\w+-\S*\.rpm", file_name)
                ):
                    logger.info("Copying TPA RPM: %s to %s" % (file,
                                                        tpa_staging.name))
                    shutil.copy(os.path.join(repo, file), tpa_staging.name)
                    os.chmod(os.path.join(tpa_staging.name, file_name), 0o777)

        cli_args.repo.append(tpa_staging.name)
        return tpa_staging
    except OSError as OSE:
        logger.exception("Failed to create temp directory or copy file.")
        raise OSE
    except Exception:
        logger.exception("Some fatal error occured! Exiting ...")
        sys.exit(1)
