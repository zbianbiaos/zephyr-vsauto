#!/usr/bin/env python3
#encoding: utf-8

import os
import sys
import json
import subprocess

# 保留的路径
preserved_paths = [ 
    '.vscode',
    'dtree.py',
    'class-pro'
]

# 排除的路径
discard_paths = [
    '**/.git',
    '**/.svn',
    '**/.hg',
    '**/CVS',
    '**/.DS_Store',
    '**/Thumbs.db',
    'zephyr-sdk-0.17.0',
]

class DirTreeNode:
    def __init__(self, name, parent):
        self.reserved = False # 文件树是否需要保留
        self.name = name
        self.children = []
        self.parent = parent

    def add_child(self, child):
        self.children.append(child)
        child.parent = self

    def set_reserved(self):
        node = self
        while node is not None:
            node.reserved = True
            node = node.parent

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

def __beautiful_defs(x):
    return x.replace(r'\"', r'"').replace(r'""', r'"')

def __beautiful_incs(x):
    return os.path.realpath(x)

def get_compiler_defs_incs_from_compile_commands(fname):
    with open(fname, 'r') as f:
        json_strs = f.read()
    j = json.loads(json_strs)

    compiler = None
    defs, incs, includes = [], [], []

    for x in j:
        root = x['directory']
        f = x['file']

        key = 'arguments'
        if 'command' in x:
            key = 'command'
        args = x[key]

        if type(args) is list:
            args = ' '.join(args)
        args = args.replace('-D ', '-D') \
                   .replace('-I ', '-I') \
                   .replace('-include ', '-include') \
                   .replace('-imacros ', '-imacros') \
                   .split()

        # 自动识别编译器
        if f.endswith('.c') and compiler == None:
            compiler = os.path.realpath(os.path.join(root, args[0]))
        for p in args:
            if p.startswith('-D') and len(p) > 2: defs.append(p[2:])
            if p.startswith('-I') and len(p) > 2: incs.append(p[2:])
            if p.startswith('-include') and len(p) > 8: includes.append(p[8:])
            if p.startswith('-imacros') and len(p) > 8: includes.append(p[8:])

        defs = list(set(defs))
        incs = list(set(incs))
        includes = list(set(includes))

    defs = [__beautiful_defs(x) for x in defs]
    defs = list(set(defs))

    incs = [__beautiful_incs(os.path.join(root, x)) for x in incs]
    incs = list(set(incs))

    includes = [__beautiful_incs(os.path.join(root, x)) for x in includes]
    includes = list(set(includes))

    defs.sort()
    incs.sort()
    includes.sort()

    return (compiler, defs, incs, includes)

def walk_root(root):
    paths = []
    for root, _, files in os.walk(root):
        for file in files:
            fname = os.path.join(root, file)
            paths.append(fname)
    return paths

def parse_deps(fname):
    with open(fname, 'r') as f:
        lines = f.readlines()
    cdeps, hdeps = [], []
    for line in lines:
        l = line.strip()
        if l.endswith('.c') or l.endswith('.cpp'):
            cdeps.append(l)
        elif l.endswith('.h') or l.endswith('.hpp'):
            hdeps.append(l)

    # 绝对路径
    cdeps = [os.path.realpath(x) for x in cdeps]
    hdeps = [os.path.realpath(x) for x in hdeps]

    # deps去重
    cdeps = list(set(cdeps))
    hdeps = list(set(hdeps))

    # 排序
    cdeps.sort()
    hdeps.sort()

    return cdeps + hdeps

def list2tree(files):
    root = DirTreeNode('/', None)
    n = 0
    for file in files:
        n += 1
        # print(f'{n}/{len(files)}: {file}')
        path = file.split('/')
        node = root
        for p in path:
            if p == '':
                continue
            if p not in [x.name for x in node.children]:
                child = DirTreeNode(p, node)
                node.add_child(child)
                node = child
            else:
                for child in node.children:
                    if child.name == p:
                        node = child
                        break
    return root

def mark_reserved(rootNode, files):
    root = rootNode
    for file in files:
        path = file.split('/')
        node = root
        for p in path:
            if p == '':
                continue
            for child in node.children:
                if child.name == p:
                    node = child
                    break
        node.set_reserved()

def getNodePath(node):
    path = ''
    while node is not None:
        path = node.name + '/' + path
        node = node.parent
    return path[1:]

def walk_tree(node, dirs=[]):
    if not node.reserved:
        dirs.append(getNodePath(node))
        return
    for child in node.children:
        walk_tree(child, dirs)

def gen_deps(prj):
    dbuild = os.path.join(prj, 'build')
    depname = os.path.join(dbuild, 'deps.txt')
    try:
        result = subprocess.run(f'ninja -C{dbuild} -t deps > {depname}', shell=True, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f'gen deps failed: \r\n{e.stdout}\r\n{e.stderr}')
        sys.exit(1)
    return depname

def generate_c_cpp_priorities(base, compiler, defs, incs, includes):
    j = {
        "configurations": [
            {
                "name": 'zephyr',
                "includePath": incs,
                "defines": defs,
                "compilerPath": compiler,
                "intelliSenseMode": 'linux-gcc-arm',
                "browse": {
                    "limitSymbolsToIncludedHeaders": True
                },
                "cStandard": "c99",
                "cppStandard": "c++11",
                "forcedInclude": includes
            }
        ],
        "version": 4
    }

    with open(os.path.join(base, '.vscode/c_cpp_properties.json'), 'w') as f:
        json_str = json.dumps(j, sort_keys=True, indent=4, separators=(',', ': '))
        f.write(json_str)

def generate_settings(base, epaths):
    j = {
        "files.associations": {
            "*.h": "c",
            "*_defconfig": "makefile",
            ".config*": "makefile"
        },
        "files.exclude": dict(zip(epaths, [True] * len(epaths)))
    }

    with open(os.path.join(base, '.vscode/settings.json'), 'w') as f:
        json_str = json.dumps(j, sort_keys=True, indent=4, separators=(',', ': '))
        f.write(json_str)

if __name__ == "__main__":
    if len(sys.argv)  < 2:
        print('Usage: python dtree.py <prj_dir>')
        sys.exit(1)
    prj_dir = sys.argv[1]
    base_dir = os.path.dirname(os.path.realpath(__file__))
    prj_dir = os.path.realpath(prj_dir)
    discard_paths = [os.path.join(base_dir, x) for x in discard_paths]
    preserved_paths = [os.path.join(base_dir, x) for x in preserved_paths]
    preserved_paths += [file for path in preserved_paths for file in walk_root(path)]

    files = []
    wfiles = walk_root(base_dir)
    for file in wfiles:
        if any([file.startswith(x) for x in discard_paths]):
            continue
        files.append(file)
    print('files count: %d' % len(files))

    root = list2tree(files)
    print('gen tree: %s' % root.name)

    fdeps = gen_deps(prj_dir)
    deps = parse_deps(fdeps)
    print(f'deps count: {len(deps)}')

    mark_reserved(root, deps)
    mark_reserved(root, preserved_paths)
    print('mark reserved done')

    edirs = discard_paths
    walk_tree(root, edirs)
    edirs = [os.path.relpath(x, base_dir) for x in edirs]
    print('walk done')

    fcmds = os.path.join(prj_dir, 'build', 'compile_commands.json')
    compiler, defs, incs, includes = get_compiler_defs_incs_from_compile_commands(fcmds)
    compiler = os.path.realpath(compiler)
    incs = [os.path.relpath(x, base_dir) for x in incs]
    incldues = [os.path.relpath(x, base_dir) for x in includes]
    os.makedirs(os.path.join(base_dir, '.vscode'), exist_ok=True)
    generate_c_cpp_priorities(base_dir, compiler, defs, incs, includes)
    generate_settings(base_dir, edirs)
    print('generate done')
