
# 使用流程

- 参考 https://docs.zephyrproject.org/latest/develop/getting_started/index.html 安装zephyr环境
- 在zephyrproject目录下把dtree.py和class-pro文件夹放入其中
- 进入class-pro/button文件夹
- 执行``west build -b chaohu``编译项目
- 返回zephyrproject目录，执行``python3 dtree.py class-pro/button``
- .vscode文件夹即会生成

# 脚本功能

脚本会在``ninja -Cbuild -t deps > deps.txt``生成依赖关系文件

解析依赖关系并根据工程目录树结构，分拣出所有与项目编译无关的文件，添加到settings.json的files.exclude字段

从compile_commands.json解析获取**编译器路径**，**头文件路径**，**宏定义***，添加到c_cpp_properties.json文件中
