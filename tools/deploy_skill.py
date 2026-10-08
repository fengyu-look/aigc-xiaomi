"""Deploy the complete self-contained skill; preserve an existing deployment."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

NAME='film-creation-library'

def link_directory(source,destination):
    if os.name=='nt':
        env=os.environ.copy()
        env['AIGC_DEPLOY_SOURCE']=str(source)
        env['AIGC_DEPLOY_TARGET']=str(destination)
        subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',
                        "New-Item -ItemType Junction -Path $env:AIGC_DEPLOY_TARGET -Target $env:AIGC_DEPLOY_SOURCE -ErrorAction Stop | Out-Null"],env=env,check=True,capture_output=True,text=True)
    else:
        destination.symlink_to(source,target_is_directory=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['link','copy'],default='link')
    parser.add_argument('--skills-dir',type=Path)
    parser.add_argument('--project-root',type=Path,help='项目位置，默认按脚本位置解析')
    parser.add_argument('--replace',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    project=(args.project_root or Path(__file__).resolve().parent.parent).resolve()
    source=(project/'skills'/NAME).resolve()
    if not source.is_dir() or not (source/'SKILL.md').is_file():
        raise ValueError('完整技能入口缺失')
    if not source.is_relative_to(project):raise ValueError('技能源目录超出项目')
    default_base=Path(os.environ['CODEX_HOME']) if os.environ.get('CODEX_HOME') else Path.home()/'.codex'
    skills_root=(args.skills_dir or default_base/'skills').resolve()
    target=skills_root/NAME
    # Validate absolute locations before moving any existing directory.
    if target.parent!=skills_root or target.name!=NAME:raise ValueError('部署目标边界校验失败')
    if target==source or (os.path.lexists(target) and target.resolve()==source):
        print(json.dumps({'Status':'already-linked','Source':str(source),'Target':str(target)},ensure_ascii=False))
        return 0
    if source.is_relative_to(target) or target.is_relative_to(source):raise ValueError('部署源与目标不能互相包含')
    exists=os.path.lexists(target)
    plan={'Mode':args.mode,'Source':str(source),'Target':str(target),'ExistingTarget':exists,
          'ReplaceRequested':args.replace,'BackupPolicy':'原目标重命名到项目.local；跨文件系统时拒绝自动删除旧目录'}
    if args.dry_run:
        print(json.dumps({'Status':'dry-run',**plan},ensure_ascii=False,indent=2));return 0
    if exists and not args.replace:raise ValueError('同名技能已存在；先查看--dry-run，需要替换时显式指定--replace')
    skills_root.mkdir(parents=True,exist_ok=True)
    stage=skills_root/(f'.{NAME}.pending-'+uuid.uuid4().hex)
    if stage.parent!=skills_root:raise ValueError('暂存目录边界错误')
    if args.mode=='link':link_directory(source,stage)
    else:shutil.copytree(source,stage,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:8]
    backup=(project/'.local/部署备份'/stamp/NAME).absolute()
    if not backup.is_relative_to(project/'.local'):raise ValueError('备份目标超出项目.local')
    moved=False
    try:
        if exists:
            backup.parent.mkdir(parents=True,exist_ok=True)
            # rename never falls back to recursively deleting a junction target.
            target.rename(backup)
            moved=True
        stage.rename(target)
    except OSError as error:
        if moved and not os.path.lexists(target):backup.rename(target)
        raise RuntimeError(f'部署失败；旧入口已保留。暂存位于{stage}。如跨盘备份，请使用同盘项目路径。') from error
    receipt={'Status':'deployed',**plan,'Backup':str(backup) if moved else None}
    receipt_path=project/'.local/部署记录.json'
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print('部署失败：'+str(error),file=sys.stderr);sys.exit(2)
