"""Refresh MD lookup offsets only after proving original content is intact."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PROJECT=Path(__file__).resolve().parent.parent
ROOT=PROJECT/'skills/film-creation-library/references/knowledge_base'
INDEX=ROOT/'91_创作小秘工作库/00_全量检索索引.json'

def raw(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return f.read()
def sha(data):return hashlib.sha256(data).hexdigest().upper()
def within(relative):
    path=(ROOT/relative.replace('\\','/')).resolve()
    if not path.is_relative_to(ROOT.resolve()):raise ValueError('索引路径越界')
    return path

def deep_sections(body, original_offset, original_length, item):
    """Index only authored sections, rejecting duplicate or misassigned task IDs."""
    matches=list(re.finditer(r'(?m)^### ((?:L\d{2}-T\d{4}|SRC\d{3}-S\d{3,4}))｜([^\r\n]+)',body))
    result=[];seen=set()
    for pos,match in enumerate(matches):
        if original_offset<=match.start()<original_offset+original_length:
            continue
        task=match[1]
        if task in seen:raise ValueError('重复深度任务ID：'+task)
        seen.add(task)
        if 'Id' in item:
            if not task.startswith(f'L{item["Id"]:02d}-T'):raise ValueError('深度任务归属库不符：'+task)
            ordinal=int(task.split('-T')[1])
            if ordinal<1 or ordinal>len(item['Topics']):raise ValueError('深度任务不对应原文候选：'+task)
        elif not task.startswith(item['SourceId']+'-S'):
            raise ValueError('深度任务归属源不符：'+task)
        end=matches[pos+1].start() if pos+1<len(matches) else len(body)
        # A later peer/higher heading ends this section even without a task ID.
        boundary=re.search(r'(?m)^#{1,3} ',body[match.end():end])
        if boundary:end=match.end()+boundary.start()
        segment=body[match.start():end]
        result.append({'TaskId':task,'Title':match[2],'Offset':match.start(),
                       'CharacterCount':len(segment),'Line':body.count('\n',0,match.start())+1,
                       'SHA256':sha(segment.encode('utf-8'))})
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    index=json.loads(raw(INDEX));changes=[]
    for item in index['SourceDocuments']+index['Libraries']:
        if 'OriginalRelativePath' in item:
            source=within(item['OriginalRelativePath'])
            if sha(source.read_bytes())!=item['OriginalSHA256']:raise ValueError('原TXT发生改变，不能自动更新基线：'+item['Name'])
            original=raw(source)
        else:
            lines=raw(within(item['MergedOriginalRelativePath'])).splitlines(keepends=True)
            original=''.join(lines[item['StartLine1Based']-1:item['EndLineInclusive']])
        if sha(original.encode('utf-8'))!=item['OriginalTextSHA256']:raise ValueError('原文来源已变化：'+item['Name'])
        body=raw(within(item['ExpandedRelativePath']))
        if body.count(original)!=1:raise ValueError('完整原文块缺失或无法唯一定位：'+item['Name'])
        offset=body.index(original);digest=sha(body.encode('utf-8'))
        sections=deep_sections(body,offset,len(original),item)
        if item['OriginalBlockOffset']!=offset or item['ExpandedSHA256']!=digest or item.get('DeepExpansions',[])!=sections:
            changes.append(item['ExpandedRelativePath'])
            item['OriginalBlockOffset']=offset;item['ExpandedSHA256']=digest
            item['DeepExpansions']=sections
    if changes and not args.dry_run:
        backup=PROJECT/'.local/索引备份'/(sha(INDEX.read_bytes())+'.json')
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_bytes(INDEX.read_bytes())
        INDEX.write_text(json.dumps(index,ensure_ascii=False,indent=2),encoding='utf-8',newline='')
    print(json.dumps({'DryRun':args.dry_run,'ChangedDocuments':changes,'OriginalBaselinesChanged':False,'DeepExpansionStatusChanged':False},ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    try:sys.exit(main())
    except (OSError,ValueError,KeyError) as error:print('刷新失败：'+str(error),file=sys.stderr);sys.exit(2)
