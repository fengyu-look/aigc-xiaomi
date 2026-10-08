"""Check portable paths, source preservation, skill format, and lookup integrity."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote

PROJECT=Path(__file__).resolve().parent.parent
SKILL=PROJECT/'skills/film-creation-library'
ROOT=SKILL/'references/knowledge_base'

def document_link_error(doc,target,project_root=PROJECT):
    """Validate local Markdown links, including Codex file :line suffixes."""
    target=unquote(target)
    if re.match(r'https?://',target):return None
    target=target.split('#',1)[0]
    line=re.search(r':([0-9]+)$',target)
    path_text=target[:line.start()] if line else target
    dest=(doc.parent/path_text).resolve()
    if not dest.is_relative_to(project_root.resolve()) or not dest.exists():
        return '项目文档链接缺失或越界：'+doc.name+' -> '+target
    if line:
        number=int(line[1])
        if not dest.is_file() or number<1 or number>len(dest.read_text(encoding='utf-8-sig').splitlines()):
            return '项目文档链接行号无效：'+doc.name+' -> '+target
    return None

def main():
    errors=[]
    config=json.loads((SKILL/'references/library_config.json').read_text(encoding='utf-8-sig'))
    if Path(config['root']).is_absolute() or (SKILL/config['root']).resolve()!=ROOT.resolve():errors.append('默认资料路径必须是Skill内相对路径')
    header=(SKILL/'SKILL.md').read_text(encoding='utf-8-sig')
    if not header.startswith('---\n') or '\n---\n' not in header:errors.append('Skill前置元数据缺失')
    else:
        front=header.split('---',2)[1]
        if not re.search(r'(?m)^name:\s*film-creation-library\s*$',front):errors.append('Skill名称与目录不符')
        if not re.search(r'(?m)^description:\s*\S.+$',front):errors.append('Skill描述缺失')
    for match in re.finditer(r'\]\(([^)]+)\)',header):
        dest=unquote(match[1]);path=(SKILL/dest).resolve()
        if not path.is_relative_to(SKILL.resolve()) or not path.exists():errors.append('Skill引用缺失或越界：'+dest)
    manifest=json.loads((ROOT/'00_分类记录.json').read_text(encoding='utf-8-sig'))
    for item in manifest['Files']:
        path=(ROOT/item['DestinationRelativePath'].replace('\\','/')).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():errors.append('原始文件缺失或越界')
        elif hashlib.sha256(path.read_bytes()).hexdigest().upper()!=item['SHA256']:errors.append('原始TXT字节发生改变：'+item['DestinationRelativePath'])
    result=subprocess.run([sys.executable,'-X','utf8',str(SKILL/'scripts/library_lookup.py'),'validate'],capture_output=True,text=True,encoding='utf-8')
    if result.returncode:errors.append(result.stderr or result.stdout)
    try:
        lookup=json.loads(result.stdout)
        errors.extend(lookup.get('Errors',[]));errors.extend(lookup.get('Warnings',[]))
    except json.JSONDecodeError:lookup={};errors.append('检索验证未返回有效JSON')
    index=json.loads((ROOT/'91_创作小秘工作库/00_全量检索索引.json').read_text(encoding='utf-8-sig'))
    if index['Root']!='.' or index['WorkingDirectory']!='91_创作小秘工作库':errors.append('索引仍含固定本机目录')
    status=json.loads((PROJECT/'docs/expansion_status.json').read_text(encoding='utf-8'))
    if {x['LibraryId'] for x in status['Libraries']}!={x['Id'] for x in index['Libraries']}:errors.append('扩写进度未覆盖全部库')
    queue=json.loads((PROJECT/'docs/deep_expansion_tasks.json').read_text(encoding='utf-8'))
    deep_by_id={section['TaskId']:(item,section) for item in index['Libraries']
                for section in item.get('DeepExpansions',[])}
    reviewed_count=0
    for task_library in queue['LibraryTasks']:
        for entry in task_library['Entries']:
            if entry['Status'] not in ('written','self_reviewed','completed'):continue
            task=entry['TaskId'];evidence=entry.get('Evidence')
            if not isinstance(evidence,dict):errors.append('已写任务缺少证据：'+task);continue
            if entry['InventoryDecision']!='included':errors.append('已写任务未纳入候选审查：'+task)
            if task not in deep_by_id:errors.append('已写任务未接入检索：'+task);continue
            item,section=deep_by_id[task]
            if evidence.get('OutputRelativePath')!=item['ExpandedRelativePath'] or evidence.get('DeepSHA256')!=section['SHA256']:
                errors.append('任务证据与深度索引不符：'+task)
            if entry['Status'] in ('self_reviewed','completed'):
                report=(PROJECT/str(evidence.get('ContentReview',''))).resolve()
                if not report.is_relative_to(PROJECT.resolve()) or not report.is_file():
                    errors.append('任务内容审查记录缺失或越界：'+task)
                elif task not in report.read_text(encoding='utf-8'):
                    errors.append('内容审查记录没有该任务ID：'+task)
                reviewed_count+=1
    for doc in [PROJECT/'README.md',*list((PROJECT/'docs').glob('*.md'))]:
        for match in re.finditer(r'\]\(([^)]+)\)',doc.read_text(encoding='utf-8')):
            error=document_link_error(doc,match[1])
            if error:errors.append(error)
    output={'OriginalTXTFiles':len(manifest['Files']),'Coverage':index['Coverage'],'LookupValidation':lookup,
            'DeepIndexedSections':len(deep_by_id),'DeepSelfReviewedTasksWithRecords':reviewed_count,'Errors':errors,
            'Scope':'结构、文件、原文、引用、可迁移路径；未测试外部生成模型或完成逐条事实校勘'}
    print(json.dumps(output,ensure_ascii=False,indent=2))
    return 1 if errors else 0

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
