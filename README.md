## 如何把「本地 Autosar 库」打成 wheel 并随仓发布

> 说明：Vercel 构建机无法直接 `pip install ./autosar`，因此需要**先在本地生成 wheel 文件**，再放到 `packages/` 目录随仓库一起推送。

---

### 1. 克隆 Autosar 源码（如已存在可跳过）

```bash
git clone https://github.com/<your-name>/autosar.git



cd autosar
python -m pip install build       
python -m build



excel2arxml/
├─ api/index.py
├─ packages/
│   └─ autosar-1.2.3-py3-none-any.whl   # 刚拷进来的文件
├─ index.html
├─ requirements.txt
└─ vercel.json


我写了一个python脚本来处理excel表格，处理完成后会生成arxml。我该如何做成网页，比如用户点开后可以上传自己的excel 然后后台运行处理后 可以下载到arxml。 问题是我没有服务器，使用github page 可以实现吗，或者用vercel 部署，有没有免费的方案


我在requirement 中填了 这些openpyxl
lxml
tomli >= 1.1.0 ; python_version < "3.11"
cfile >= 0.4.0
pandas
加入还依赖于本地的一个叫autosar的库怎么编写requirement， 之前我需要cd 到autosar 下然后执行pip install .
我的架构是
├─ api/index.py 
├─ autosar
├─ index.html           
├─ requirements.txt
└─ vercel.json