"""Synthetic BIFF12/XLSB reference cache fixtures; no private source workbook in git."""
import struct
import zipfile
from pathlib import Path
from engineering_xlsb_reference import ReferenceWorkbookCache,reference_foundations


def rec(id,payload):
    identifier=[]
    while id>=128:
        identifier.append((id&255)|0x80);id>>=8
    identifier.append(id)
    # Excel XLSB record IDs are multi-byte, with low 8-bit shift for next byte.
    size=len(payload);length=[]
    while size>=128:
        length.append((size&127)|128);size>>=7
    length.append(size)
    return bytes(identifier+length)+payload


def text(s):
    b=s.encode("utf-16le")
    return struct.pack("<I",len(s))+b


def row(i):
    return rec(0,struct.pack("<I",i))


def shared_cell(col,index):
    return rec(7,struct.pack("<II",col,0)+struct.pack("<I",index))


def number_cell(col,value):
    return rec(5,struct.pack("<II",col,0)+struct.pack("<d",value))


def make_reference_fixture(path):
    strings=["CPT REFERENCE","Easting","Norting","Settlement (mm)","min. FOS",
             "Footing Type","CPT-A1-292-100","Raft","Water Level (m)",
             "net area ratio in the cone, a (a - factor)","CPT reference",
             "Combined CPTs","Lvl","qc","Ic","ground"]
    sst=rec(0x19f,struct.pack("<II",len(strings),len(strings)))
    for s in strings:sst+=rec(0x13,b"\\x00".decode("unicode_escape").encode()+text(s))
    workbook=b""
    for i,(name,rel) in enumerate([("Input","rId1"),("Summary","rId2"),("Combined CPTs","rId3")],1):
        workbook+=rec(0x19c,struct.pack("<II",0,i)+text(rel)+text(name))
    inputs=row(0)+shared_cell(0,9)+number_cell(1,.8)
    inputs+=row(1)+shared_cell(0,8)+number_cell(1,2)
    inputs+=row(2)+shared_cell(0,10)+shared_cell(1,6)
    summary=row(1)
    for i,idx in [(2,0),(3,1),(4,2),(14,3),(20,4),(6,5)]:
        summary+=shared_cell(i,idx)
    summary+=row(2)+shared_cell(2,6)+number_cell(3,421092.37)
    summary+=number_cell(4,2928336.25)+number_cell(14,71.544074)
    summary+=number_cell(20,2.430584)+shared_cell(6,7)
    profile=row(0)+shared_cell(0,6)+row(1)+shared_cell(0,12)+shared_cell(1,13)+shared_cell(2,14)
    profile+=row(2)+number_cell(0,3.46)+number_cell(1,5)+number_cell(2,7)
    rels='<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    for i in range(1,4):
        rels+=f'<Relationship Id="rId{i}" Type="http://schemas.microsoft.com/office/2006/relationships/worksheet" Target="worksheets/sheet{i}.bin"/>'
    rels+="</Relationships>"
    with zipfile.ZipFile(path,"w") as archive:
        archive.writestr("xl/workbook.bin",workbook)
        archive.writestr("xl/sharedStrings.bin",sst)
        archive.writestr("xl/_rels/workbook.bin.rels",rels)
        for n,body in enumerate([inputs,summary,profile],1):
            archive.writestr(f"xl/worksheets/sheet{n}.bin",body)


def test_reference_cache_reads_explicit_engineering_source_fields(tmp_path):
    f=tmp_path/"reference.xlsb"
    make_reference_fixture(f)
    with ReferenceWorkbookCache(f) as workbook:
        assert workbook.input_parameters()["Water Level (m)"][1]==2
        assert workbook.summary()["cone_ratio"]==.8
        rows=workbook.foundation_summary()
        assert len(rows)==1
        assert abs(rows[0]["Settlement (mm)"]-71.544074)<1e-8
        profiles=workbook.mapped_profiles()
        assert profiles["CPT-A1-292-100"]==[(3.46,5.,7)]
    foundations=reference_foundations(f)
    assert foundations[0].reference=="CPT-A1-292-100"
    assert foundations[0].metrics["fos"]==2.430584
    assert foundations[0].metrics["settlement_mm"]==71.544074
