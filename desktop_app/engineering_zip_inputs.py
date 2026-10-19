"""Safe, deterministic ZIP ingestion for CPT project soundings.

Never extracts path traversal, links, unsafe file types or decompression bombs.
The source folder is retained beside the ZIP so audit paths are stable after
the app closes. No input data is uploaded to a server.
"""
from __future__ import annotations
import os
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

SUPPORTED={".gef",".gff",".pdf"}


def read_zip_sources(zip_path,*,max_files=2500,max_uncompressed=600_000_000,
                     per_file_limit=40_000_000):
    source=Path(zip_path)
    if source.suffix.lower()!=".zip" or not source.is_file():
        raise ValueError("Select a real CPT ZIP archive")
    collected=[];total=0
    with zipfile.ZipFile(source) as archive:
        for entry in archive.infolist():
            if entry.is_dir():continue
            name=entry.filename.replace("\\","/")
            parts=PurePosixPath(name)
            if (parts.is_absolute() or ".." in parts.parts or
                any(p in ("",".") for p in parts.parts)):
                raise ValueError("Unsafe ZIP path (absolute/traversal/empty)")
            if stat.S_IFMT((entry.external_attr>>16)&0xffff)==stat.S_IFLNK:
                raise ValueError("ZIP contains a symbolic link; CPT sources must be regular files")
            if Path(name).suffix.lower() not in SUPPORTED:continue
            if entry.file_size>per_file_limit:
                raise ValueError("CPT source exceeds per-file safety limit")
            total+=entry.file_size
            if total>max_uncompressed:
                raise ValueError("ZIP exceeds maximum uncompressed CPT project size")
            collected.append((entry,str(parts)))
            if len(collected)>max_files:
                raise ValueError("ZIP contains more CPT sources than the configured safe limit")
    if not collected:
        raise ValueError("ZIP has no supported GEF/GFF/PDF inputs")
    return collected


def extract_project_zip(zip_path,destination=None):
    source=Path(zip_path)
    entries=read_zip_sources(source)
    target=(Path(destination) if destination else
            source.parent/(source.stem+"_CPT_Source"))
    if target.is_dir():
        # Reuse prior local extraction only when every expected input exists
        # with the same uncompressed file size. Never overwrite user edits.
        existing=[target/name for _,name in entries]
        if all(p.is_file() and p.stat().st_size==entry.file_size
               for p,(entry,_) in zip(existing,entries)):
            return target,existing
        raise ValueError("Previous extraction differs from ZIP. Choose another extraction folder.")
    target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cpt_zip_",dir=target.parent) as tmp:
        staging=Path(tmp)/"project"
        staging.mkdir()
        extracted=[]
        with zipfile.ZipFile(source) as archive:
            for item,name in entries:
                dest=staging/name
                dest.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(item,"r") as inp,dest.open("wb") as out:
                    shutil.copyfileobj(inp,out,1_048_576)
                extracted.append(name)
        os.replace(staging,target)
    return target,[target/name for name in extracted]
