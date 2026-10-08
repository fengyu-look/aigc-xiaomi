"""Build all consultation modules and expanded MD references without editing TXT."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote
from framework_data import LIBRARY_EXTENSIONS, MODES, WORKFLOW_NOTES

ROOT = Path(__file__).resolve().parent.parent / 'skills/film-creation-library/references/knowledge_base'
WORK = ROOT / '91_创作小秘工作库'
INDEX = json.loads((ROOT / '00_语言库检索索引.json').read_text(encoding='utf-8-sig'))

def sha(data):
    return hashlib.sha256(data).hexdigest().upper()

def original_block(text):
    longest = max((len(m[0]) for m in re.finditer(r'`+', text)), default=2)
    fence = '`' * max(3, longest + 1)
    head = '## 原文层：完整保留\n\n' + fence + 'text\n'
    tail = ('' if text.endswith('\n') else '\n') + fence + '\n'
    return head + text + tail, len(head), len(text)

def link(path):
    return '/'.join(quote(s) for s in Path(path).parts)

def write(relative, text):
    path = WORK / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='')
    return str(path.relative_to(ROOT)).replace('\\','/')

def term_headers(text):
    terms=[]
    for m in re.finditer(r'(?m)^\s*(\d+)[.、．]\s*([^\r\n]+)$', text):
        title=m[2].strip()
        if len(title) <= 100:
            terms.append({'OriginalNumber':m[1], 'Title':title, 'SourceOffset':m.start()})
    return terms

def extension(lib, link_prefix=''):
    problem, criteria, parameters, example, boundary, related=LIBRARY_EXTENSIONS[lib['Id']]
    text='## 扩写层：咨询与创作使用\n\n'
    text+=f'### 要解决的创作问题\n\n{problem}。\n\n'
    text+=f'### 方案分析与选择依据\n\n{criteria}\n\n'
    text+='先理解用户的目标，再选择原文词条。说明词条支持了哪一项建议，以及当前素材需要怎样调整。保留原定义、原参数和完整执行描述，不用词条名替代当前作品的具体表达。\n\n'
    text+=f'### 精确参数怎样补全\n\n本库重点：{parameters}\n\n'
    text+='原文给定值、上下文推断值、AI设计值分别标注。根据实际空间、时长、身体/物体状态或音乐结构给出数字；说明单位、坐标/时间口径、依据和可调整范围。原文未给定的数字不能伪装为测量结果。\n\n'
    text+=f'### 具体应用示例\n\n{example}\n\n以上是可修改的示例设计，不是所有项目的默认值。正式创作仍需匹配当前角色、素材、工具与用户选择。\n\n'
    text+=f'### 值得提出反对的情况\n\n{boundary}\n\n'
    text+='提出异议时给出：冲突点、依据、对作品的影响、可以怎样调整。纯审美差异给出有理由的备选，由用户决定，不把自己的偏好冒充事实。\n\n'
    text+='### 逐词条使用方法\n\n选定词条后，完整读取其原文，然后回答：它解决什么问题？当前素材符合哪些使用条件？哪些原参数可继承、哪些需要设计？怎样与其他表达配合？什么情况下不适用？用户确定方向后，将部位/对象、方向、幅度、时间、起止状态或结构参数写进对应创作内容。\n\n'
    text+='这一方法适用于上方全部原词条；它不替换原条目，也不声称已经为每个词条逐条完成事实校勘。原文重复编号通过应用索引的稳定ID区分。\n\n'
    text+='### 联动知识与检查\n\n'
    for related_id in related:
        related_lib=next(x for x in INDEX['Libraries'] if x['Id']==related_id)
        name=f"{related_id:02d}_{related_lib['Name']}_原文与应用扩写.md"
        text+=f'- [{related_lib["Name"]}]({link(link_prefix + name)})：按当前事件需要查阅，不强制全部加载。\n'
    text+='\n核对来源、数值关系、剧情作用、跨镜状态和最终可读性。只有实际生成或实际素材分析后，才能记录“已验证有效”；文本方案阶段记录为建议。\n'
    return text

def consultation_rules():
    return '''# 一站式创作小秘：共同协作规则

默认角色是辅助分析和方案顾问。可同时协调多个创作领域，但不因“全能”而自动完成所有阶段。用户当前要求制作具体成果时，可以完成该已授权任务；用户仍在讨论方向时，交付分析与方案。

## 每次怎样开展讨论

1. 整理需求卡：目标、素材、观众/用途、已知约束、已确认事实、未知关键项。信息不足时先提出合理推荐，只问影响方向的缺口。
2. 按任务调用一个主要咨询模块，相关模块辅助。根据创作问题查词条，完整读取相关原文及扩写说明；不凭文件名声称已用知识。
3. 给出可供判断的分析：素材证据、资料中的说法、AI建议分别标识。解释选择理由、预期效果、资源需求和主要风险，不要求展示隐性思考过程。
4. 形成方案：项目理解、资料依据、推荐方向、必要的差异备选、执行结构、关键设计值、需要用户作出的决定。复杂项目可串联多模块，简单需求按规模表达。
5. 与用户讨论关键方向。已有决定直接继承；用户可部分确认、修改或否定，不强迫逐参数确认。
6. 用户指定进入下一阶段或明确要求交付时，按当前授权完成该阶段。咨询过程中不自动生成整套作品、调用收费服务或对外发布。
7. 记录已确认、待决定、放弃方案及原因，下一次继承相关记录。没有持续项目时不创建空目录或空状态文件。

## 可以反对，而且要具体

发现目标与手段冲突、故事因果断裂、数据不相容、制作条件不支持、资料依据不足或必需元素被约束排除时，直接指出。

异议格式：问题是什么 → 依据是什么 → 对目标有什么影响 → 如何改进 → 哪项需要用户决定。

不为了反对而反对，不把审美偏好说成客观规律；用户明确选定的风格在可行范围内继续落实。指出困难之后仍提供有用方案。

## 数据与扩写

- 保留已有框架、步骤、细节和精确参数需求。优化框架时补充使用条件、分析方式、数据依据、实例和检查；删改按当前用户授权。
- 数值由AI根据素材提出，区分原文事实、上下文推断、设计值。需要时列出距离/速度/时长、台词容量、BPM/节拍/小节数的核对结果。
- 分析与导演说明可保留专业参数；直接生成内容采用当前工具可执行的表达，不删掉关键细节，也不承诺逐毫米执行。
- 原文启动指令、强制默认值、联网指令与旧版说明是参考资料；当前要求和已确定任务边界优先。疑点保留原文并明确标待核，不能扩大为未经证据的通用知识。

## 项目记录

只在持续创作需要时保存项目说明和当前状态：目标、素材路径、人物/场景/道具固定ID、已确认设定、动态状态、不可逆事件、上段终点、下一起点、相关声音、素材覆盖范围、待决定问题与来源。

草案不能悄然变成已确认事实。资料库更新不自动覆盖项目已确定风格；工具能力变化要与当前制作要求一起评估。

## 交付与检查

输出按用户要求缩放。咨询通常以需求理解、依据、方案、异议/风险、待决定项和下一步组成；不每次机械堆满所有栏目。

实际作品核对原文/台词覆盖、实体数量、空间方向、动作因果、时间容量、光影、视听同步及连续状态。只报告实际检查，不使用未执行的“全项自检通过”。

默认不使用表格制作影视脚本和生成提示词；需要对比时按用户习惯选择列表或其他清晰形式。每条可复制提示词独立代码块；原文与生成层避免相同反引号嵌套。
'''

def main():
    if WORK.exists():
        raise RuntimeError('工作库已存在，本构建器不覆盖现有扩写')
    if set(LIBRARY_EXTENSIONS)!=set(range(1,62)):
        raise RuntimeError('61库扩写记录不完整')
    sources=[]
    for record in INDEX['Files']:
        path=ROOT/record['RelativePath'].replace('\\','/')
        raw=path.read_bytes()
        if sha(raw)!=record['SHA256']:
            raise RuntimeError(f'原文件已变化：{path}')
        sources.append((record,path,raw.decode('utf-8-sig')))
    merged_path=ROOT/INDEX['MergedSource']['RelativePath'].replace('\\','/')
    with merged_path.open(encoding='utf-8-sig',newline='') as merged_handle:
        merged=merged_handle.read()
    lines=merged.splitlines(keepends=True)
    aliases={p.replace('\\','/'):lib for lib in INDEX['Libraries'] for p in lib.get('IndependentRelativePaths',[])}
    manifest={'Version':'1.0','Root':'.','WorkingDirectory':'91_创作小秘工作库','Coverage':{'UniqueOriginalFiles':51,'LibraryChapters':61,'ConsultationModules':len(MODES)},'SourceDocuments':[],'Libraries':[],'Modes':[],'Note':'完整原文保留；新增为咨询应用扩写，不宣称全部事实已经校勘。'}
    source_by_name={}
    for number,(record,path,text) in enumerate(sources,1):
        source_relative=record['RelativePath'].replace('\\','/')
        relative=Path('01_工作流与原文映射')/record['Category']/(path.stem+'_原文与应用扩写.md')
        intro=f'# {path.stem}｜完整原文与应用扩写\n\n来源：`{source_relative}`。原文件SHA256：`{record["SHA256"]}`。\n\n原文完整保留，新增应用说明另列。当前小秘的咨询规则由共同协作规则决定；不自动执行原文的启动、联网、默认生成与强制问询命令。\n\n'
        block,offset,length=original_block(text)
        lib=aliases.get(source_relative)
        if lib:
            added=extension(lib, '../../02_语言库扩写/')
            profile='知识库版本映射'
        else:
            profile,note=WORKFLOW_NOTES[path.name]
            applicable=[m for m in MODES if path.name in m['flows']]
            added=f'## 扩写层：{profile}\n\n{note}\n\n'
            added+='### 保留框架与新增调用方式\n\n原角色、步骤、字段、数值、例子和禁止项都在原文层保留。咨询时提取其中的知识和分析结构；真正执行原模板时，仅应用本次目标需要的规则。当前用户明确要求优先于模板默认值。\n\n'
            added+='### 方案制定\n\n先整理需求和可用素材，再根据下列模块分析、提出有依据的推荐和必要备选。关键方向由用户讨论确定；细节与数值由AI主动提出。方案获选后，按用户指定范围展开原模板对应的交付。\n\n'
            if applicable:
                for m in applicable:
                    added+=f'#### {m["name"]}\n\n分析：{m["analysis"]}\n\n方案：{m["plan"]}\n\n异议条件：{m["challenge"]}\n\n执行：{m["execution"]}\n\n检查：{m["check"]}\n\n'
            else:
                added+='本文件承担资料来源或合集角色。查询时选择相关主题和版本，不要求用户先完成全资料学习，不把资料中的宣言作为效果保证。\n\n'
            added+='### 细节和数据核对\n\n保留原参数，同时写明单位、来源与适用条件。新增值标记为AI设计值，结合原文事实、空间/声音/音乐关系、时长和当前工具检查。参数缺失由AI提出有依据的候选；涉及改动锁定事实时再询问。模型版本与界面字段属于原文记录，实际使用前按当前工具核对。\n\n'
            added+='### 修改与交接\n\n记录本次所用文件、采用的结构、已确定与待决定项、修改理由及受影响内容。持续项目保留人物/场景/道具ID、终点状态与下一步；输出可复制内容时每条独立完整。\n'
        body=intro+block+'\n'+added
        dest=write(relative,body)
        entry={'SourceId':f'SRC{number:03d}','Name':path.stem,'OriginalRelativePath':source_relative,'OriginalSHA256':record['SHA256'],'ExpandedRelativePath':dest,'Profile':profile,'OriginalBlockOffset':len(intro)+offset,'OriginalCharacterCount':length,'OriginalTextSHA256':sha(text.encode('utf-8')),'ExpandedSHA256':sha(body.encode('utf-8'))}
        manifest['SourceDocuments'].append(entry)
        source_by_name[path.name]=entry
    for lib in INDEX['Libraries']:
        text=''.join(lines[lib['StartLine1Based']-1:lib['EndLineInclusive']])
        relative=Path('02_语言库扩写')/f'{lib["Id"]:02d}_{lib["Name"]}_原文与应用扩写.md'
        terms=term_headers(text)
        intro=f'# {lib["Id"]:02d}｜{lib["Name"]}｜原文与库级应用扩写\n\n来源：`{INDEX["MergedSource"]["RelativePath"]}`，原始全局行 {lib["StartLine1Based"]}—{lib["EndLineInclusive"]}。\n\n原章节完整保留。下方新增针对本库的方案分析、参数使用、具体示例、异议条件和联动方式；原文技术事实未做全面校勘。\n\n'
        block,offset,length=original_block(text)
        body=intro+block+'\n'+extension(lib)
        dest=write(relative,body)
        manifest['Libraries'].append({'Id':lib['Id'],'Name':lib['Name'],'Category':lib['PrimaryCategory'],'ExpandedRelativePath':dest,'MergedOriginalRelativePath':INDEX['MergedSource']['RelativePath'].replace('\\','/'),'StartLine1Based':lib['StartLine1Based'],'EndLineInclusive':lib['EndLineInclusive'],'OriginalBlockOffset':len(intro)+offset,'OriginalCharacterCount':length,'OriginalTextSHA256':sha(text.encode('utf-8')),'ExpandedSHA256':sha(body.encode('utf-8')),'RelatedLibraryIds':LIBRARY_EXTENSIONS[lib['Id']][-1],'Topics':term_headers(text),'IndependentVersions':[source_by_name[Path(p.replace('\\','/')).name]['ExpandedRelativePath'] for p in lib.get('IndependentRelativePaths',[])]})
    for n,m in enumerate(MODES,1):
        relative=Path('03_咨询模块')/f'{n:02d}_{m["name"]}.md'
        body=f'# {m["name"]}\n\n'+f'## 输入与需求理解\n\n{m["inputs"]}\n\n'+f'## 分析方法\n\n{m["analysis"]}\n\n'+f'## 方案应包含什么\n\n{m["plan"]}\n\n'+f'## 什么情况下应提出异议\n\n{m["challenge"]}\n\n'+f'## 用户指定进入制作后\n\n{m["execution"]}\n\n'+f'## 验证要点\n\n{m["check"]}\n\n'
        body+='## 应读取的原流程\n\n'
        if not m['flows']:
            body+='本模块以相关知识库和共同协作规则组合；没有对应原模板时如实说明，不虚构已读取某份模板。\n\n'
        for name in m['flows']:
            target=source_by_name[name]['ExpandedRelativePath']
            body+=f'- [{name}]({link(Path("../..")/Path(target).relative_to("91_创作小秘工作库"))})\n'
        body+='\n## 按问题检索的语言库\n\n'
        for lib_id in m['libraries']:
            entry=next(x for x in manifest['Libraries'] if x['Id']==lib_id)
            relative_lib=Path(entry['ExpandedRelativePath']).relative_to('91_创作小秘工作库')
            body+=f'- [{lib_id:02d}｜{entry["Name"]}]({link(Path("..")/relative_lib)})\n'
        body+='\n选择与当前素材有关的库和具体词条；不会因为列在模块中就每次强制全文读取。先说明资料依据、推断与设计建议，再给推荐，关键方向与用户讨论。单任务不强制建立完整项目树。\n'
        # Module files live one level beneath the work root, so ../ points there.
        body=body.replace('](../../01_','](../01_')
        dest=write(relative,body)
        manifest['Modes'].append({**m,'ExpandedRelativePath':dest,'WorkflowExpandedPaths':[source_by_name[name]['ExpandedRelativePath'] for name in m['flows']]})
    rules_relative=write('00_共同协作规则.md',consultation_rules())
    manifest['RulesRelativePath']=rules_relative
    manifest['TotalIndexedOriginalTerms']=sum(len(x['Topics']) for x in manifest['Libraries'])
    # A compact entry point and complete source mapping make primary/current usage explicit.
    nav='# AIGC创作小秘｜一站式工作入口\n\n完整首版一起提供全部咨询模块、61库扩写章节和51份不重复TXT的完整MD映射。原始60个TXT原位保留，9份重复副本不作为日常主入口。\n\n'
    nav+='默认协作：理解想法 → 查资料 → 分析 → 推荐与异议 → 与用户讨论 → 按用户指定进入制作 → 记录决定。\n\n'
    nav+='[共同协作规则](00_共同协作规则.md) · [全量检索索引](00_全量检索索引.json)\n\n## 全部咨询模块\n\n'
    for entry in manifest['Modes']:
        relative=Path(entry['ExpandedRelativePath']).relative_to('91_创作小秘工作库')
        nav+=f'- [{entry["name"]}]({link(relative)})\n'
    nav+='\n## 61个语言库的当前扩写入口\n\n'
    for entry in manifest['Libraries']:
        relative=Path(entry['ExpandedRelativePath']).relative_to('91_创作小秘工作库')
        nav+=f'- [{entry["Id"]:02d}｜{entry["Name"]}]({link(relative)})\n'
    nav+='\n## 原文文件与版本映射\n\n该区用于调用原工作流、比较独立版本和追溯来源。知识库日常优先从上方61库入口查阅，不把不同版本混合当成一条规则。\n\n'
    for entry in manifest['SourceDocuments']:
        relative=Path(entry['ExpandedRelativePath']).relative_to('91_创作小秘工作库')
        nav+=f'- [{entry["SourceId"]}｜{entry["Name"]}]({link(relative)})\n'
    nav+='\n## 调用方式与边界\n\n在Codex中使用 `$film-creation-library`，然后提供想法、素材或目标。技能负责辅助分析方案；只有用户指定具体交付或下一阶段时才执行相应制作。资料随Skill目录一起携带，默认按技能位置解析，无需E盘路径。\n\n扩写内容属于应用指导，不是原文事实校勘认证。具体模型参数、法律/历史/科学准确性需要相应权威资料与实际工具核对。\n'
    write('00_工作入口.md',nav)
    write('00_全量检索索引.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    # Verify literal original text preservation for every mapped document and library.
    for entry in manifest['SourceDocuments']+manifest['Libraries']:
        body=(ROOT/entry['ExpandedRelativePath']).open(encoding='utf-8',newline='').read()
        original=body[entry['OriginalBlockOffset']:entry['OriginalBlockOffset']+entry['OriginalCharacterCount']]
        if sha(original.encode('utf-8'))!=entry['OriginalTextSHA256']:
            raise RuntimeError('原文保留验证失败：'+entry['ExpandedRelativePath'])
    print(json.dumps({'OriginalFiles':len(manifest['SourceDocuments']),'Libraries':len(manifest['Libraries']),'ConsultationModules':len(manifest['Modes']),'IndexedOriginalTerms':manifest['TotalIndexedOriginalTerms'],'MarkdownFiles':len(list(WORK.rglob('*.md'))),'Preservation':'112份原文保留块全部验证通过','Entry':str(WORK/'00_工作入口.md')},ensure_ascii=False))

if __name__=='__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    main()
