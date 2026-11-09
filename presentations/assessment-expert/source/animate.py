"""Inject slide transitions + auto-playing entrance animations into a pptxgenjs deck.

usage: python animate.py in.pptx anim_plan.json out.pptx
anim_plan.json: {"<slideNo>": [{"name": objectName, "fx": fade|float|zoom|wipe, "delay": ms, "dur": ms}]}
"""
import json
import re
import sys
import zipfile

from lxml import etree

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
NS = {"p": P}

src, plan_path, dst = sys.argv[1:4]
plan = json.load(open(plan_path))


class Ids:
    def __init__(self):
        self.n = 4

    def __call__(self):
        self.n += 1
        return self.n


def tgt(spid):
    return f'<p:tgtEl><p:spTgt spid="{spid}"/></p:tgtEl>'


def set_visible(ids, spid):
    return (f'<p:set><p:cBhvr><p:cTn id="{ids()}" dur="1" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst></p:cTn>'
            f'{tgt(spid)}<p:attrNameLst><p:attrName>style.visibility</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:to><p:strVal val="visible"/></p:to></p:set>')


def anim_effect(ids, spid, dur, flt):
    return (f'<p:animEffect transition="in" filter="{flt}"><p:cBhvr><p:cTn id="{ids()}" dur="{dur}"/>'
            f'{tgt(spid)}</p:cBhvr></p:animEffect>')


def anim_prop(ids, spid, dur, attr, frm, to, frm_float=False):
    fv = f'<p:fltVal val="{frm}"/>' if frm_float else f'<p:strVal val="{frm}"/>'
    return (f'<p:anim calcmode="lin" valueType="num"><p:cBhvr additive="base">'
            f'<p:cTn id="{ids()}" dur="{dur}" decel="100000" fill="hold"/>{tgt(spid)}'
            f'<p:attrNameLst><p:attrName>{attr}</p:attrName></p:attrNameLst></p:cBhvr>'
            f'<p:tavLst><p:tav tm="0"><p:val>{fv}</p:val></p:tav>'
            f'<p:tav tm="100000"><p:val><p:strVal val="{to}"/></p:val></p:tav></p:tavLst></p:anim>')


PRESET = {"fade": (10, 0), "float": (42, 0), "zoom": (53, 16), "wipe": (22, 8)}


def effect(ids, spid, fx, delay, dur):
    pid, sub = PRESET[fx]
    head = (f'<p:par><p:cTn id="{ids()}" presetID="{pid}" presetClass="entr" presetSubtype="{sub}" '
            f'fill="hold" grpId="0" nodeType="withEffect"><p:stCondLst><p:cond delay="{delay}"/></p:stCondLst><p:childTnLst>')
    body = set_visible(ids, spid)
    if fx == "fade":
        body += anim_effect(ids, spid, dur, "fade")
    elif fx == "float":
        body += anim_effect(ids, spid, dur, "fade")
        body += anim_prop(ids, spid, dur, "ppt_x", "#ppt_x", "#ppt_x")
        body += anim_prop(ids, spid, dur, "ppt_y", "#ppt_y+0.05", "#ppt_y")
    elif fx == "zoom":
        body += anim_prop(ids, spid, dur, "ppt_w", "0", "#ppt_w", True)
        body += anim_prop(ids, spid, dur, "ppt_h", "0", "#ppt_h", True)
        body += anim_effect(ids, spid, dur, "fade")
    elif fx == "wipe":
        body += anim_effect(ids, spid, dur, "wipe(left)")
    return head + body + "</p:childTnLst></p:cTn></p:par>"


def shapes(xml_bytes):
    root = etree.fromstring(xml_bytes)
    out = {}
    for tag in ("sp", "pic", "graphicFrame", "cxnSp"):
        for el in root.iter(f"{{{P}}}{tag}"):
            c = el.find(".//p:cNvPr", NS)
            if c is not None:
                out[c.get("name")] = (c.get("id"), tag)
                ph = el.find(".//p:nvPr/p:ph", NS)
                if ph is not None:
                    out["ph:" + ph.get("type", "body")] = (c.get("id"), tag)
    return out


def timing(entries, shp):
    ids = Ids()
    effects, bld, seen = [], [], set()
    for e in sorted(entries, key=lambda e: e["delay"]):
        if e["name"] not in shp:
            raise SystemExit(f"object {e['name']} not found on slide")
        spid, tag = shp[e["name"]]
        effects.append(effect(ids, spid, e["fx"], int(e["delay"]), int(e["dur"])))
        if spid in seen:
            continue
        seen.add(spid)
        if tag == "sp":
            bld.append(f'<p:bldP spid="{spid}" grpId="0" animBg="1"/>')
        elif tag == "graphicFrame":
            bld.append(f'<p:bldGraphic spid="{spid}" grpId="0"><p:bldAsOne/></p:bldGraphic>')
    return ('<p:timing><p:tnLst><p:par><p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot"><p:childTnLst>'
            '<p:seq concurrent="1" nextAc="seek"><p:cTn id="2" dur="indefinite" nodeType="mainSeq"><p:childTnLst>'
            '<p:par><p:cTn id="3" fill="hold"><p:stCondLst><p:cond delay="indefinite"/>'
            '<p:cond evt="onBegin" delay="0"><p:tn val="2"/></p:cond></p:stCondLst><p:childTnLst>'
            '<p:par><p:cTn id="4" fill="hold"><p:stCondLst><p:cond delay="0"/></p:stCondLst><p:childTnLst>'
            + "".join(effects) +
            '</p:childTnLst></p:cTn></p:par></p:childTnLst></p:cTn></p:par>'
            '</p:childTnLst></p:cTn>'
            '<p:prevCondLst><p:cond evt="onPrev" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:prevCondLst>'
            '<p:nextCondLst><p:cond evt="onNext" delay="0"><p:tgtEl><p:sldTgt/></p:tgtEl></p:cond></p:nextCondLst>'
            '</p:seq></p:childTnLst></p:cTn></p:par></p:tnLst>'
            + (f'<p:bldLst>{"".join(bld)}</p:bldLst>' if bld else "") + '</p:timing>')


TRANSITION = '<p:transition spd="slow"><p:fade/></p:transition>'

zin = zipfile.ZipFile(src)
zout = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
count = 0
for item in zin.infolist():
    data = zin.read(item.filename)
    m = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", item.filename)
    if m:
        n = m.group(1)
        xml = data.decode("utf-8")
        assert "<p:timing" not in xml and "<p:transition" not in xml
        inject = TRANSITION + (timing(plan[n], shapes(data)) if plan.get(n) else "")
        if "</p:clrMapOvr>" in xml:
            xml = xml.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + inject, 1)
        else:
            xml = xml.replace("</p:cSld>", "</p:cSld>" + inject, 1)
        data = xml.encode("utf-8")
        count += len(plan.get(n, []))
    zout.writestr(item, data)
zout.close()
print(f"animated {count} effects")
