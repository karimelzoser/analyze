import zipfile
import pytest
from engineering_zip_inputs import extract_project_zip,read_zip_sources


def _make(path,entries):
    with zipfile.ZipFile(path,"w") as z:
        for name,body in entries.items():z.writestr(name,body)


def test_safe_project_zip_selection_and_stable_source_reuse(tmp_path):
    file=tmp_path/"CPT project.zip"
    _make(file,{"01 GEF FILES/A.GEF":"#EOH=\n0 1 0.03",
                 "01 GEF FILES/B.gff":"#EOH=\n0 1 0.03",
                 "helper/readme.txt":"unrelated"})
    out,files=extract_project_zip(file)
    assert len(files)==2
    assert all(f.is_file() for f in files)
    new,found=extract_project_zip(file)
    assert new==out and {x.name for x in found}=={"A.GEF","B.gff"}


def test_reject_path_traversal_without_writing_outside_output(tmp_path):
    source=tmp_path/"unsafe.zip"
    _make(source,{"../outside.GEF":"bad","#SOURCE/normal.GEF":"good"})
    with pytest.raises(ValueError,match="Unsafe ZIP path"):
        extract_project_zip(source)
    assert not (tmp_path/"outside.GEF").exists()


def test_zip_bomb_and_malformed_extension_rejected(tmp_path):
    source=tmp_path/"unsafe.zip"
    _make(source,{"cpt.GEF":"x"*1000})
    with pytest.raises(ValueError,match="per-file safety"):
        read_zip_sources(source,per_file_limit=500)
    bad=tmp_path/"notes.zip"
    _make(bad,{"notes.txt":"Not CPT"})
    with pytest.raises(ValueError,match="no supported"):
        read_zip_sources(bad)
