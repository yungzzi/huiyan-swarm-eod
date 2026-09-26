# 目录

- [欢迎来到 *Swarm-Rescue*](#欢迎来到-swarm-rescue)
- [竞赛介绍](#竞赛介绍)
- [仿真环境](#仿真环境)
- [安装](#安装)
- [环境元素](#环境元素)
- [为你的无人机编程](#为你的无人机编程)
- [联系方式](#联系方式)

# 欢迎来到 *Swarm-Rescue*

通过这个项目，你将在仿真中消除威胁……教会一群无人机如何找到炸弹、把它们运送到处理中心，并尽可能快地完成任务。

你的工作是开发自己的无人机控制器。在竞赛中，每支参赛队伍都会在全新的、未知的地图上接受评估。冠军将由一套基于多重标准的评分系统决定：处理速度、探索效率、已处理炸弹数量、无人机剩余生命值，等等。

*Swarm-Rescue* 是用于仿真无人机、并描述所用地图、无人机以及地图中各类元素的环境。

[访问 GitHub 仓库 *Swarm-Rescue*](https://github.com/emmanuel-battesti/swarm-rescue) • [官网](https://emmanuel-battesti.github.io/swarm-rescue-website/) • [更新日志](https://github.com/emmanuel-battesti/swarm-rescue/blob/main/CHANGELOG.md)

本挑战只需要基础的 *Python* 知识，强调创造力、问题解决能力和算法思维。成功更多取决于无人机协同方面的创新方法，而不是高深的编程技巧。

# 竞赛介绍

## 任务

目标很简单：探索一片未知区域（比如倒塌建筑的地下室），探测炸弹，抓取它们，并把它们运送到处理中心。

每支队伍拥有一支由 10 架无人机组成的机群，配备传感器和通信设备。你的任务是**为这些无人机编程，使它们 100% 自主**，用 *Python* 编写。

它们需要相互协作，应对故障、通信中断和突发状况，才能成功完成任务。所有开发**完全在这个仿真环境内**进行，地图复杂度逐步提升。

最终评估将在组织方设计的、参赛者无法获得的多张未知地图上进行。每个方案都会在同一台计算机上测试，并计算与性能相关的得分。

## 红队与蓝队（两阶段任务）

有些竞赛在**同一个启动器**上使用两种角色：

1. **红队（`place`）**——探索未知地图，并使用 `place_bomb` 执行器**放置炸弹**。每架无人机携带的炸弹数量有限（由评估计划中的 `initial_bombs_per_drone` 指定）。任务结束时，仿真器会写出一份列出炸弹位置的 JSON 文件。
2. **蓝队（`rescue`）**——在同一地图几何结构上运行，并从该 JSON 文件（`bombs_file`）加载炸弹。无人机像经典任务那样搜索、抓取并处理炸弹；评分基于处理情况、探索、生命值和时间。

示例命令（请使用项目的虚拟环境 Python，例如 `.venv/bin/python`）：

```bash
# 红队（place）示例
.venv/bin/python -m swarm_rescue.launcher -c config/competition_place_eval_plan.yml
# 蓝队（rescue）示例
.venv/bin/python -m swarm_rescue.launcher -c config/competition_rescue_eval_plan.yml
```

YAML 字段：每个场景的 `team_mode`、`initial_bombs_per_drone`、`bombs_file`（`auto` = 同一次运行中上一阶段 place 生成的 JSON）。参见 `config/competition_place_eval_plan.yml` 和 `config/competition_rescue_eval_plan.yml`。

## 评分

根据最终评估之前场景的演进情况，分数计算方式可能会有细微调整。

任务在以下情况结束时终止：
- 达到最大仿真时间步（*max timestep limit*）。
- 超过最大实际执行时间（*max walltime limit*，通常为 2 到 5 分钟）。
当两个限制中的任意一个被触发时，游戏结束。如果你的算法足够快，你会先触及"最大时间步限制"；如果算法太慢，你会先触及"最大墙钟时间限制"。

**蓝队（rescue）**——满分 100 分：
- **已处理炸弹（60%）：** 送达处理中心的百分比。
- **无人机生命值（20%）：** 位于返回区内的无人机生命值。
- **效率（20%）：** 根据本轮已耗费的时间步评分——耗时不超过时间步上限的一半即得满分，达到上限得 0 分，中间线性变化（与红队 Time 分的约定相同）。所有炸弹处理完毕时本轮立即结束；若跑到上限仍未处理完所有炸弹，此项得 0 分。

**红队（place）**——满分 100 分，四个组成部分（默认权重 50/20/20/10，可通过 `place_scoring` 配置）：
- **地图提交（50%）：** [`MapExplorationScorer`](src/swarm_rescue/tools/map_exploration_scoring.py) 将经由 `submit_exploration_map()` 提交的二值栅格与真值"仅墙体"栅格（由地图的真实墙体实体构建，处理中心、返回区和干扰区不算墙体）进行比对。得分来自对墙体表层（1.0）和深层内部（0.0）的命中率；对距离任何真实墙体超过 10 px 的预测像素会进行扣分，并按墙体表层像素数归一化。`map = clamp(credit - penalty)`——纯建图准确度（不混入内部时间因素；时间加分是下面单独的组成部分）。未提交 → 该项得 0 分。
- **炸弹放置（20%）：** place 批次结束后，参考蓝队提交方案（在标定地图上通过 `select-reference-blues` 选出）会针对每份红队 `*_bombs.json` 运行 rescue。蓝队表现越差得分越高（`difficulty = min(100, (100 - blue_score) × 2)`，取均值或中位数），并按放置完成度缩放（`placed / expected`，expected = 每轮的 `initial_bombs_per_drone × number_drones`）。失败的参考运行会被剔除；成功参考不足时该项得分记为 `partial`。
- **墙体破坏（20%）：** 每枚炸弹产生一次圆形爆炸，半径为 `blast_radius`——它是**地图较短边的一个比例**（默认 `0.12`，在 Map04 上约 135 px）。被爆炸并集覆盖的墙体（同一份"仅墙体"栅格）计为已破坏，边界框架墙按 `boundary_wall_weight`（默认 0.5）折算。得分是加权覆盖率**除以该地图的理论最优值**（在炸弹数量与半径相同的条件下做确定性贪心覆盖），因此满分意味着"达到该地图可达的最佳布局水平"——同一张地图上所有队伍的参考值完全一致。
- **时间（10%）：** 根据本轮已耗费的时间步评分——耗时不超过上限的一半即得满分，达到上限得 0 分，中间线性变化（`time_metric: timestep`）。

多轮运行（竞赛计划中的 `nb_rounds: 2`）按场景取平均；红队炸弹分在各轮之间取平均；蓝队得分在各红队炸弹布局之间取平均。

无人机返航生命值**不**计入红队得分。

# 仿真环境

Swarm-Rescue 基于 2D 仿真库 [**Simple-Playgrounds**](https://github.com/mgarciaortiz/simple-playgrounds)（SPG）的修改版代码构建，该库使用 **Pymunk** 物理引擎和 **Arcade** 游戏引擎。

具体来说，这意味着：
- 无人机和物体具有质量和惯性（不会瞬间停止）。
- 碰撞由物理引擎处理。
- 仿真器在每个时间步管理"感知—动作—通信"循环。

# 安装

安装说明请参阅 [`INSTALL.md`](INSTALL.md) 文件。

# 环境元素

## 无人机

无人机是 *Simple-Playgrounds* 中的一种**智能体（agent）**。
无人机由附着在一个 *Base* 上的多个身体部件组成。

无人机通过两个第一人称视角传感器**感知周围环境**：
- *Lidar*（激光雷达）传感器
- *Semantic*（语义）传感器

无人机还配有通信系统。

无人机配备了可以**估计自身位置和朝向**的传感器。我们有两类：
- 绝对测量：用于位置的 *GPS* 和用于朝向的磁力*罗盘*。
- 相对测量：*里程计*，提供相对于无人机上一位置的位置和朝向。

它们还拥有生命点（或生命值），每次与环境或其他无人机碰撞都会减少，降至零时即被摧毁。无人机被摧毁时会从地图上消失。
无人机可以通过其数据属性 *drone_health* 访问该数值。

### Lidar 传感器

文件 `src/swarm_rescue/simulation/ray_sensors/drone_lidar.py`，类 *DroneLidar*。

它模拟一个具有以下规格的激光雷达传感器：

- *fov*（视场角）：360 度
- *resolution*（射线数量）：181
- *max range*（传感器最大量程）：300 像素

测量距离上加入了高斯噪声，以模拟真实世界的条件。
由于*视场角*（fov）为 360°，第一个值（-Pi 弧度处）和最后一个值（Pi 处）应当相同。

你可以在 `src/swarm_rescue/solutions/my_drone_lidar_communication.py` 文件中找到使用激光雷达的示例。

要可视化激光雷达传感器数据，需要将 *GuiSR* 类的参数 *draw_lidar_rays* 设为 *True*。

### 语义传感器

文件 `src/swarm_rescue/simulation/ray_sensors/drone_semantic_sensor.py`，在类 *DroneSemanticSensor* 中描述。

语义传感器无需数据处理即可判定无人机周围物体的性质。

- *fov*（视场角）：360 度
- *max range*（传感器最大量程）：200 像素
- *resolution*：在视场角内均匀分布的射线数量：35

由于 *fov* 为 360°，第一个（-Pi 弧度处）和最后一个值（Pi 处）应当相同。

你可以在 `examples/example_semantic_sensor.py` 文件中找到使用语义传感器的示例。

在本次竞赛中，语义传感器只能探测 *Bomb*（炸弹）、*DisposalCenter*（处理中心）和其他 *Drones*（无人机），**不能**探测 *Walls*（墙体）（请使用 Lidar 进行墙体探测与避障）。

每条传感器射线提供一个具有以下属性的数据对象：
- *data.distance*：到最近被探测物体的距离
- *data.angle*：射线角度（弧度）
- *data.entity_type*：`DroneSemanticSensor.TypeEntity` 取值（`BOMB`、`DISPOSAL_CENTER`、`DRONE`、……）
- *data.grasped*：布尔值，指示该物体是否已被抓取

注意：如果探到墙体，距离和角度都会返回 0，以防通过该传感器使用墙体数据。

距离测量上施加了高斯噪声，以模拟真实传感器的局限性。

要可视化语义数据，需要将 *GuiSR* 类构造函数的 *draw_semantic_rays* 参数设为 *True*。

### GPS 传感器

文件 `src/swarm_rescue/simulation/drone/drone_sensors.py`，在类 *DroneGPS* 中描述。

该传感器给出沿水平轴和垂直轴的位置向量。
位置 (0, 0) 位于地图中心。
数据中加入了噪声以模拟 GPS 噪声。这不仅仅是高斯噪声，而是遵循一阶自回归模型的噪声。

如果你想启用噪声可视化，需要将 *GuiSR* 类构造函数的 *enable_visu_noises* 参数设为 *True*。

### 罗盘传感器

文件 `src/swarm_rescue/simulation/drone/drone_sensors.py`，在类 *DroneCompass* 中描述。

该传感器给出无人机的朝向。
朝向随无人机逆时针旋转而增大。取值在 -Pi 到 Pi 之间。
数据中加入了噪声以模拟罗盘噪声。这不仅仅是高斯噪声，而是遵循一阶自回归模型的噪声。

如果你想启用噪声可视化，需要将 *GuiSR* 类构造函数的 *enable_visu_noises* 参数设为 *True*。

### 里程计传感器

文件 `src/swarm_rescue/simulation/drone/drone_sensors.py`，在类 *DroneOdometer* 中描述。

该传感器通过一个包含三项关键测量的数组提供相对定位数据：
- `dist_travel`：上一时间步行进的距离（像素）
- `alpha`：当前位置相对于上一帧的相对角度（弧度）
- `theta`：上一时间步内的朝向变化（旋转量，弧度）

这些测量都相对于无人机的上一位置。通过对里程计读数随时间积分，你可以在绝对定位（GPS）不可用时估计无人机的当前位置。

在穿越地图上的 GPS 拒止区域（例如 No-GPS 区域）时，这一能力至关重要。

角度 alpha 和 theta 随无人机逆时针旋转而增大，取值在 -Pi 到 Pi 之间。
对数据的三个部分分别加入了高斯噪声，使其看起来像真实噪声。

![odometer values](img/odom.png)

如果你想启用噪声可视化，需要将 *GuiSR* 类构造函数的 *enable_visu_noises* 参数设为 *True*。它还会通过绘制估计路径来演示里程计数值的积分。

### 通信

无人机可以通过通信系统与附近的队友交换信息：
* 每架无人机可以与 250 像素范围内的所有其他无人机通信。
* 消息在每个仿真时间步发送和接收。
* 你可以通过 `define_message_for_all()` 方法自定义消息内容
* 接收到的消息可通过 `received_messages` 属性获取

你可以在 `src/swarm_rescue/solutions/my_drone_lidar_communication.py` 中找到无人机通信的实用示例。

### 执行器

在每个时间步，你必须为执行器提供取值。

有 3 个值用于控制无人机的运动：
- *forward*：-1 到 1 之间的浮点数。沿纵向施加力。
- *lateral*：-1 到 1 之间的浮点数。沿横向施加力。
- *rotation*：-1 到 1 之间的浮点数。控制旋转速度。

要与世界交互，你可以*抓取*某些*可抓取*物体。要处理一枚*炸弹*，你必须：
1. 靠近它
2. 将 *grasper* 值设为 1 来*抓取*它
3. 把它运送到处理中心
4. 将 *grasper* 值设为 0 来释放它

*grasper* 执行器是二值的：
- 0：释放（未携带任何物体）
- 1：抓取（正携带一个物体）

**仅红队：** *place_bomb* 执行器是二值的（上升沿会在无人机位置放置一枚炸弹，前提是库存仍有剩余）：
- 0：本步不放置
- 1：尝试放置一枚炸弹

用无人机类上的 `carried_bombs_count()` 查询剩余携带容量。`control()` 片段示例：

```python
command = {
    "forward": 1.0,
    "lateral": 0.0,
    "rotation": 0.0,
    "grasper": 0,
    "place_bomb": 1 if self.carried_bombs_count() > 0 else 0,
}
```

当一枚炸弹被某架无人机抓取后，它对这架无人机的语义传感器就是"透明"的。这一设计让无人机更容易导航，射线不会被携带的物体遮挡。

你可以在 `examples/` 和 `src/swarm_rescue/solutions/` 中几乎所有文件里找到执行器使用示例。

## 场地（Playground）

无人机在 *Playground* 中行动和感知。

一个 *playground* 由场景元素组成，这些元素可以是固定的或可移动的。无人机可以抓取某些场景元素。
在这个 *Swarm-Rescue* 仓库中，包含全部元素（无人机除外）的 playground 被称为"地图（Map）"。

### 坐标系

playground 使用标准笛卡尔坐标系：

* 位置 `(x, y)`：
  - 原点 (0,0) 位于地图中心。
  - `x`：水平位置（向右为正）
  - `y`：垂直位置（向上为正）

* 朝向 `theta`：
  - 以弧度度量，介于 -π 和 π 之间
  - 随逆时针旋转而增大
  - 当 `theta` = 0 时，无人机朝向右侧（正 x 轴）

* 地图尺寸：
  - 地图尺寸为 [width, height]，width 沿 x 轴，height 沿 y 轴
  - 所有测量单位均为像素

## 炸弹

*Bomb*（炸弹）在地图上显示为黄色精灵。它是可抓取物体，必须送达配对的处理中心。

**处理流程：**
1. 探测炸弹（语义传感器：`TypeEntity.BOMB`）
2. 靠近并抓取（`grasper = 1`）
3. 运送到处理中心
4. 在处理中心内释放（`grasper = 0`），或让它被抓握状态下与处理中心碰撞

当炸弹进入其关联的处理中心时，仿真器会奖励携带它的无人机，并将炸弹从 playground 中移除。

**炸弹类型：**
- **静态**（大多数）：保持在固定位置
- **动态**：沿预定路径移动：
  - 沿其既定路线往返移动
  - 如果被丢在路线之外，会沿直线移动以重新回到路线上
  - 由于在移动，可能更难处理

抓取炸弹的实用示例见 `examples/example_semantic_sensor.py`。

动态炸弹示例见 `examples/example_moving_bomb.py` 文件。

## 处理中心

*Disposal Center*（处理中心）是地图上的一块红色区域。每枚炸弹都关联到某一个处理中心实例（`Bomb(disposal_center=...)`）；只有这一配对才会触发处理和计分。

语义传感器类型：`TypeEntity.DISPOSAL_CENTER`。

示例见 `examples/example_semantic_sensor.py`。

## 返回区

*Return Area*（返回区）是地图上的一块蓝色区域，无人机应在任务结束时停留在那里。
最终得分的一部分根据该区域计算：任务结束时返回该返回区的无人机生命值点数，与任务开始时这些无人机生命值点数之比。
如果地图中没有*返回区*，则按地图中所有无人机的生命值百分比计算得分。

该返回区对任何传感器都不可见，但布尔数据属性 *is_inside_return_area* 会给出无人机是否位于返回区内的信息。
*返回区*总是靠近*处理中心*，且无人机总是从该区域开始任务。

## API 命名（仿真器元素）

较新版本在代码和文档中采用炸弹处理的叙事。如果你要改编旧版方案或外部教程，请更新以下符号：

| 旧名称 | 当前名称 |
|-------------|--------------|
| `WoundedPerson` | `Bomb` |
| `RescueCenter` | `DisposalCenter` |
| `TypeEntity.WOUNDED_PERSON` | `TypeEntity.BOMB` |
| `TypeEntity.RESCUE_CENTER` | `TypeEntity.DISPOSAL_CENTER` |
| `grasped_wounded_persons()` | `grasped_bombs()` |
| `number_wounded_persons`（地图 / 启动器） | `number_bombs` |
| 地图 JSON `"type": "rescue_center"` | `"type": "disposal_center"` |
| 精灵图 `character_v2.png` / `rescue_center.png` | `bomb.png` / `disposal_center.png` |

游戏玩法未变：抓取、运送、与处理中心碰撞、奖励、移除。

精灵图位于 `src/swarm_rescue/resources/`。修改美术生成逻辑后要重新生成它们：

```bash
.venv/bin/python -m swarm_rescue.tools.generate_resource_sprites
```

## 特殊区域

有些区域会改变无人机的能力。它们也可以调用*干扰器（disablers）*。它们对所有传感器都不可见！
- **无通信区（No-Communication Zone，透明黄色）：** 切断所有无线电通信。
- **无 GPS 区（No-GPS Zone，透明灰色）：** GPS 和罗盘不再工作。依靠里程计！
- **击杀区（Kill Zone，或称停用区，透明粉色）：** 立即摧毁任何进入的无人机。

# 为你的无人机编程

## 代码架构

你的代码位于 `src/swarm_rescue/solutions` 目录。你只需要修改这个文件夹中的文件。

一个重要文件是 `src/swarm_rescue/solutions/my_drone_eval.py`。你要在这里告诉仿真器使用哪个无人机类：MyDroneEval 类必须继承你的无人机类。

`src/swarm_rescue/launcher.py` 是使用你的代码启动无人机机群的主程序文件。这个文件执行评估所需的全部流程。

它会启动 10 架你自定义的无人机、在你选定的地图上运行，并给出最终得分。

## 无人机的"大脑"

你必须创建一个继承自 `DroneAbstract` 的类。这个类就是你无人机的"大脑"。它必须实现两个关键方法：

1.  `define_message_for_all()`：在这里定义无人机发送给邻居的信息。
2.  `control()`：这是你逻辑的核心。该方法在每个时间步被调用，必须返回执行器命令（移动、转向等）。

**黄金法则：** 在你的代码中，**只**使用传感器数据（例如 `measured_gps_position()`），而不要使用仿真的真值（例如 `true_position()`）。这对于为真值不可得的实际竞赛条件做准备至关重要。

## 有用的目录

- `src/swarm_rescue/solutions`：**你的代码。** 这里提供了示例。
- `src/swarm_rescue/maps`：可用的仿真地图。
- `examples/`：独立的示例脚本，帮助理解各项功能（用键盘控制无人机、可视化 Lidar 等）。
- `src/swarm_rescue/tools`：工具，例如根据图像创建地图。
- `src/swarm_rescue/simulation`：仿真器的核心。**不要修改这些文件。**

## 评估计划（Evaluation Plan）

### 什么是评估计划？

评估计划定义你的无人机将在哪些场景中接受测试。它完全通过 YAML 文件配置，让你可以指定使用哪些地图、哪些特殊区域，以及每个场景运行多少轮——无需改动任何 Python 代码。

**为什么要用它？**
- 评估者可以轻松地在多种场景下测试你的方案。
- 你可以在自定义地图和条件下测试自己的代码。
- 输出选项（报告、视频）也由同一个文件控制。

---

### YAML 配置结构

你的主配置文件（例如 `config/competition_rescue_eval_plan.yml`）应当如下所示：

```yaml
stat_saving_enabled: true          # 保存统计并生成 PDF 报告（true/false）
state_recording_enabled: true      # 记录实体状态到 .npz 以便回放（true/false，默认：true）
video_capture_enabled: false       # 将完整视频编码为 .avi（true/false，默认：false）

evaluation_plan:
  - map_name: MapIntermediate01
    nb_rounds: 2
    config_weight: 1
    zones_config: []
  - map_name: MapIntermediate02
    nb_rounds: 1
    config_weight: 1
    zones_config: []
  - map_name: Map04
    nb_rounds: 1
    config_weight: 1
    zones_config: []
  - map_name: Map04
    nb_rounds: 1
    config_weight: 1
    zones_config: [NO_COM_ZONE, NO_GPS_ZONE, KILL_ZONE]
  - map_name: Map02
    nb_rounds: 1
    config_weight: 1
    zones_config: [NO_COM_ZONE, NO_GPS_ZONE, KILL_ZONE]
```

**顶层字段：**
- `stat_saving_enabled`：保存统计并生成 PDF 报告（`true`/`false`）
- `state_recording_enabled`：将实体位置记录到 `.npz` 以便轻量回放（`true`/`false`，默认：`true`）
- `video_capture_enabled`：记录全分辨率视频到 `.avi`（`true`/`false`，默认：`false`）

在 ~/results_swarm_rescue 目录中生成统计报告、状态记录和任务视频，主要是为竞赛评估者准备的。
状态记录（.npz）是默认的记录方式（约 150 KB/轮），取代了旧式的 AVI 视频编码（50-200 MB/轮）。
你可以通过 'state_recording_enabled' 和 'video_capture_enabled' 开关控制记录。

用以下命令回放录像：
```bash
.venv/bin/python -m swarm_rescue.launcher --replay <recording.npz>
```
回放控制：SPACE 播放/暂停，LEFT/RIGHT 快进快退，UP/DOWN 调速，Q 退出。

**evaluation_plan：**
场景列表，每个场景包含：
- `map_name`：要使用的地图（见 `src/swarm_rescue/maps`）
- `nb_rounds`：该场景重复多少次
- `config_weight`：在最终得分中的重要性
- `zones_config`：要激活的特殊区域列表：
  - `NO_COM_ZONE`：禁用无人机通信
  - `NO_GPS_ZONE`：禁用 GPS 定位
  - `KILL_ZONE`：摧毁进入的无人机
  - 空列表 `[]`：不激活任何特殊区域

### 快速开始：运行一次评估

1. 按需编辑你的 YAML 文件。
2. 用你的配置运行启动器：
   ```bash
   python src/swarm_rescue/launcher.py --config config/competition_rescue_eval_plan.yml
   ```
3. 如果启用了，结果（报告/视频）会出现在 `~/results_swarm_rescue` 中。

**注意：**
生成的报告和视频供评估者使用。

### 回放录像

状态记录（`.npz`）可以被可视化回放，以复查无人机/炸弹的轨迹：

```bash
.venv/bin/python -m swarm_rescue.launcher --replay <recording.npz>
```

回放控制：**SPACE** 播放/暂停，**LEFT/RIGHT** 前后跳转 ±30 帧，**UP/DOWN** 调速，**Q** 退出。窗口启动时处于暂停状态——按 SPACE 开始回放。

### 无头模式运行（无显示）

仿真器支持**无头模式（headless mode）**，这对于在没有显示器或 GPU 的远程服务器上运行评估至关重要。

#### 基本用法

加上 `--headless`（或 `-H`）标志即可在不打开窗口的情况下运行：

```bash
python src/swarm_rescue/launcher.py --headless --config config/competition_rescue_eval_plan.yml
```

**重要：** 只有在已有 X11 服务器运行（即使不可见）时，该命令才可用。`--headless` 标志告诉 arcade 不要显示窗口，但它仍需要 X11 显示来创建 OpenGL 上下文。

#### 在无显示的服务器上运行

如果你在既没有 X11 的服务器上，或遇到 OpenGL/显示错误，请使用 `xvfb-run` 创建虚拟帧缓冲：

```bash
# 如需要，安装 xvfb
sudo apt-get install xvfb

# 用虚拟显示运行
xvfb-run -s "-screen 0 1920x1080x24" python src/swarm_rescue/launcher.py --headless --config config/competition_rescue_eval_plan.yml
```

这让仿真器即使没有物理显示器也能创建 OpenGL 上下文，从而在无头环境中进行状态记录和渲染。

### API：EvalConfig 与 EvalPlan

你也可以用编程方式创建评估计划：

```python
from swarm_rescue.simulation.reporting.evaluation import EvalConfig, EvalPlan
from swarm_rescue.simulation.elements.sensor_disablers import ZoneType

# 创建一个简单场景
easy_config = EvalConfig(map_name="MyMapEasy01")

# 包含所有特殊区域的场景
hard_config = EvalConfig(
    map_name="Map04",
    zones_config=(ZoneType.NO_COM_ZONE, ZoneType.NO_GPS_ZONE, ZoneType.KILL_ZONE),
    nb_rounds=3,
    config_weight=2
)

# 把场景加入计划
plan = EvalPlan()
plan.add(easy_config)
plan.add(hard_config)
```
你可以在以下文件的 main() 函数中看到以编程方式创建评估计划的示例：
- src/swarm_rescue/maps/map_01.py
- src/swarm_rescue/maps/map_02.py
- src/swarm_rescue/maps/map_03.py
- src/swarm_rescue/maps/map_04.py
- src/swarm_rescue/maps/map_05.py

### 预置的评估计划

`config/` 目录包含开箱即用的评估计划 YAML 文件：

**可用配置：**
- `competition_place_eval_plan.yml`——红队 / `place` 示例
- `competition_rescue_eval_plan.yml`——蓝队 / `rescue` 示例

**用法示例：**
```bash
# 本地蓝队（rescue）运行
python src/swarm_rescue/launcher.py --config config/competition_rescue_eval_plan.yml

# 本地红队（place）运行
python src/swarm_rescue/launcher.py --config config/competition_place_eval_plan.yml
```

## 代码详解

### *simulation* 目录

顾名思义，`src/swarm_rescue/simulation` 文件夹包含仿真器的软件。它包含六个子目录：
- *drone*：无人机、其传感器和执行器的定义。
- *elements*：环境各元素（墙体、炸弹、处理中心、返回区等）的定义。
- *gui_map*：图形界面、键盘管理、playground 等。
- *ray_sensors*：射线传感器（lidar、语义传感器等）以及传感器使用的着色器。
- *reporting*：计算得分和生成 PDF 评估报告的工具。
- *utils*：各种函数和实用工具。

其中的文件**不得**修改。

一个重要文件是 `src/swarm_rescue/simulation/gui_map/gui_sr.py`，它包含类 *GuiSR*。要用键盘操作"#0 号"无人机，请把 *GuiSR* 构造函数中的 `use_keyboard` 参数设为 `True`。要启用用于调试的噪声可视化，请设置 `enable_visu_noises=True`；它还会绘制估计的里程计路径。

### *maps* 目录

该目录 `src/swarm_rescue/maps` 包含无人机使用的地图。随着新任务的开发，可能会加入新地图。你也可以基于现有地图创建自己的地图。

每个地图文件都包含一个 main 函数，可以直接执行该文件来观察地图。此时地图以静止无人机运行。参数 `use_mouse_measure` 被设为 `True`，因此在屏幕上点击时测量工具处于激活状态。

每张地图都必须继承类 *MapAbstract*。

### *solutions* 目录

该目录 `src/swarm_rescue/solutions` 将存放你的方案。目前其中的代码是行为简单的示例实现。把它当作灵感并更进一步：编写定义你的无人机以及它们如何与环境交互的代码。

每架无人机都必须继承类 *DroneAbstract*。你有 2 个必需的成员函数：`define_message_for_all()` 用于定义无人机之间发送的消息，`control()` 用于返回每个时间步要执行的动作。

请记住，同一份代码会在 10 架无人机上各自运行。每架无人机都是你的 Drone 类的一个实例。

在 `control()` 中进行计算时，只使用传感器和通信数据，不要直接访问内部成员。特别地，不要使用真实的 `position` 和 `angle` 变量；而应使用 `measured_gps_position()` 和 `measured_compass_angle()` 获取无人机的位置和朝向。这些值带有噪声（更真实），并且可能被特殊区域改变。

无人机的真实位置可以通过 `true_position()` 和 `true_angle()` 访问（或直接用变量 `position` 和 `angle`），但这**仅**用于调试或日志。

`src/swarm_rescue/solutions` 中提供了示例实现，帮助你上手：
- `my_drone_random.py`——演示基本的 lidar 传感器使用和执行器控制
- `my_drone_lidar_communication.py`——演示如何实现无人机间通信与 lidar
- `my_drone_motionless.py`——静止无人机的最小实现（可用作起步模板）

### *examples* 目录

在仓库根目录的 `examples/` 文件夹中，你会找到帮助理解关键概念的独立程序。特别是：
- `example_display_lidar.py` 在图表上展示 lidar 的可视化（含噪声）。
- `example_com_disabler.py` 演示无人机之间的通信以及 *No Com Zone* 和 *Kill Zone* 的效果。当通信可行时，两架无人机之间会画出一条线。
- `example_disablers.py` 演示各个干扰区。
- `example_gps_disablers.py` 演示 *No GPS Zone* 和 *Kill Zone* 的效果。绿圈是 GPS 位置；红圈是仅用里程计的估计值。
- `example_keyboard.py` 展示如何使用键盘进行开发或调试。可用按键包括：Up/Down（前进/后退）、Left/Right（转向）、Shift+Left/Right（横向移动）、W（抓取）、L（lidar 射线）、S（语义射线）、P（GPS 位置）、C（通信）、M（打印消息）、Q（退出）、R（重置）。
- `example_mapping.py` 展示如何创建占据栅格地图。
- `example_pid_rotation.py` 用 PID 控制朝向。
- `example_pid_translation.py` 用 PID 控制平移。
- `example_return_area.py` 使用 `is_inside_return_area` 检测无人机是否在返回区内。
- `example_semantic_sensor.py` 展示语义传感器和执行器，抓取一枚炸弹并把它带到处理中心。
- `example_moving_bomb.py` 展示沿预定路径移动的炸弹。
- `example_static_semantic_sensor.py` 演示与其他无人机和炸弹相关的语义传感器射线。
- `random_drones.py` 展示许多无人机在空地上随机飞行。
- `random_drones_intermediate_1.py` 展示在 `map_intermediate_01` 中的随机飞行。

### *tools* 目录

在 `src/swarm_rescue/tools` 中，你可以找到创建地图、进行测量等实用工具。特别是：
- `image_to_map.py` 根据黑白图像构建地图。
- `check_map.py` 显示不带无人机的地图；点击会打印坐标——对设计或修改地图很有用。

## 提交

竞赛结束时，把你的方案提交给评估者。评估者会使用同一套软件来评估你的方案。

只需提供：
- 运行你仿真无人机的代码，必须来自 `src/swarm_rescue/solutions` 目录。
- 填写正确的 `team_info.yml` 文件。
- 运行你的无人机所需的任何新依赖列表。

提交之前，请在项目上以及最终的 `teamNNN_evalstep.zip` 上运行 `./check_submission.sh`。完整的提交规则以及检查器所校验内容的详细清单，请参阅 [`doc/participants/03-提交检查与打包.md`](doc/participants/03-提交检查与打包.md)。

## 各种提示

### 退出执行

- 启动地图后要优雅退出，请在仿真窗口中按 `Q`（退出当前轮）。
- 要立即退出整个程序，请在仿真窗口中按 `E`（退出所有轮）。

### 启用一些可视化

*GuiSR* 类可以用以下参数构造（括号内为默认值）：
- `draw_zone`：True。绘制特殊区域（无通信区、无 GPS 区、击杀区）。
- `draw_lidar_rays`：False。绘制 lidar 射线。
- `draw_semantic_rays`：False。绘制语义传感器射线。
- `draw_gps`：False。绘制 GPS 位置。
- `draw_com`：False。显示通信范围以及通信中无人机之间的连线。
- `print_rewards`：False。
- `print_messages`：False。
- `use_keyboard`：False。
- `use_mouse_measure`：False。点击打印鼠标位置。
- `enable_visu_noises`：False。
- `filename_video_capture`：None 表示禁用；否则为输出视频文件名（.avi）。
- `filename_state_recording`：None 表示禁用；否则为输出状态记录文件名（.npz）。

### 在终端打印 FPS 性能

通过修改 `src/swarm_rescue/simulation/gui_map/gui_sr.py` 顶部的全局变量 `DISPLAY_FPS = True`，可以定期在控制台显示程序 FPS。
详见 `src/swarm_rescue/simulation/utils/fps_display.py`。

### 显示你自己的画面

在 *DroneAbstract* 中，你可以重写两个函数来绘制叠加层：
- `draw_top_layer()`：在所有图层之上绘制。
- `draw_bottom_layer()`：在所有其他图层之下绘制。

例如，在 `draw_top_layer()` 中调用 `self.draw_identifier()` 来绘制无人机标识。

### 创建新地图

创建自定义地图有助于复现特定场景、对算法的局部进行压力测试，以及在受控条件下比较策略。
它也让你能在最终于未知地图上评估之前，先原型化各种挑战（墙体布局、炸弹位置和特殊区域）。

要添加新地图，你必须在 `src/swarm_rescue/maps` 中创建并添加两个文件：
- `map_<name>.py`——定义 Map 类（继承自 `MapAbstract`）。在你 Map 类的 `__init__` 中粘贴 `image_to_map.py` 打印出的初始化行（例如 `self._size_area`、`self._disposal_center`、`self._disposal_center_pos`、`self._bombs_pos`），使地图参数与转换结果完全一致。实现 `build_playground()` 来设置无人机起始位置，并调用添加墙体/箱体的辅助函数。
- `walls_<name>.py`——包含 `image_to_map.py` 生成的辅助函数（脚本会写出 `generated_code.py`）。把生成的辅助函数（例如 `add_walls(playground)` 和 `add_boxes(playground)`）复制到 `walls_<name>.py`，并在 `map_<name>.py` 中导入它们。

分步流程

1. 把你的地图画成 PNG 图像，使用清晰一致的颜色：
   - 墙体：纯黑（RGB 0,0,0），约 10 px 粗，以保证检测稳健。
   - 炸弹：亮黄色（建议 RGB 255,255,0），直径约 25–40 px。
   - 处理中心：纯红（RGB 255,0,0）。
2. 编辑 `src/swarm_rescue/tools/image_to_map.py` 中的 `img_path` 指向你的 PNG 并运行脚本。该工具是交互式的，会用 OpenCV（`cv2.imshow`）显示中间图像；按任意键继续（`cv2.waitKey(0)`）。成功后它会：
   - 写出一个包含辅助函数（墙体/箱体）的 `generated_code.py`，并且
   - 在控制台打印若干 Python 初始化行。
3. 把 `generated_code.py` 中的辅助函数复制到新文件 `src/swarm_rescue/maps/walls_<name>.py`。
4. 把控制台打印的初始化行复制到 `src/swarm_rescue/maps/map_<name>.py` 中你 `Map` 类的 `__init__` 里。重要：请复制这些确切的赋值，使你的地图参数与转换器输出一致：
   - `self._size_area`
   - `self._disposal_center`
   - `self._disposal_center_pos`
   - `self._bombs_pos`
   这些值确保地图尺寸、处理中心位置和炸弹坐标与转换结果完全相同（`image_to_map.py` 的控制台输出是权威来源）。
5. 在 `map_<name>.py` 中实现 `build_playground()`，以：
   - 导入并调用 `walls_<name>.py` 中的辅助函数来添加墙体/箱体，
   - 定义无人机起始区域/位置（转换器不会自动创建无人机起点），
   - 添加你的场景所需的任何返回区或额外元素。
6. 使用 `src/swarm_rescue/tools/check_map.py` 进行可视化验证（显示不带无人机的地图，点击时打印坐标）。可视化验证后，运行一次短仿真对地图做冒烟测试：
```bash
python3 src/swarm_rescue/launcher.py --config config/competition_rescue_eval_plan.yml
```
注意事项与故障排查
- 要复制的确切变量：运行 `image_to_map.py` 时，控制台输出包含要粘贴到 `map_<name>.py` 中的 Python 行。特别是要把 `self._size_area`、`self._disposal_center`、`self._disposal_center_pos` 和 `self._bombs_pos` 的赋值复制到你 Map 类的 `__init__` 中。
- 颜色检测：`image_to_map.py` 使用 HSV/亮度阈值检测炸弹的黄色色调和处理中心的红色。如果某个特定色调检测失败（例如黄色与绿色混淆），请在 `src/swarm_rescue/tools/image_to_map.py` 中调整阈值（在那里调整黄色/绿色阈值）。README 有意指向该工具进行颜色调优，而不是罗列众多变体。
- 无人机起始位置：转换器不设置无人机起始位置。请在 `map_<name>.py` 中显式添加它们——有关惯用写法，参见现有的 `map_*.py` 示例。
- 小元素与粗细：在源 PNG 中保持墙体有合理粗细（约 8–12 px），以免检测时碎片化。
- 最终检查：创建两个文件（`map_<name>.py`、`walls_<name>.py`）并用 `check_map.py` 验证后，运行一次短仿真以就地验证地图。

# 快速上手

欢迎来到 Swarm-Rescue！本节将帮助你快速搭建环境，并用自定义无人机控制器运行第一次仿真。

## 安装

按照 [INSTALL.md](INSTALL.md) 搭建环境、安装依赖并排查常见问题。支持的平台包括 Ubuntu（推荐）和 Windows（配合 WSL2 或 Git Bash）。

## 快速开始示例

安装完成后，你可以用以下命令启动默认仿真：

```bash
python3 src/swarm_rescue/launcher.py
```

## 可视化 Lidar 与检测射线

你可以通过两种方式在 GUI 中可视化每架无人机的感知：

- Lidar 射线（距离传感器射线）
- 语义射线（物体检测射线）

### 运行时热键（GUI 窗口打开时）

- `L`：切换 lidar 射线
- `S`：切换语义射线

这些开关仅在非无头模式下可用。

### 从代码启用（GuiSR 构造函数）

如果你自己实例化 GUI，可以直接启用射线叠加层：

```python
from swarm_rescue.simulation.gui_map.gui_sr import GuiSR

gui = GuiSR(
    playground=playground,
    draw_lidar_rays=True,
    draw_semantic_rays=True,
)
```

### Lidar 图表窗口（每架无人机）

你也可以通过以下方式构造无人机来打开 lidar 图表窗口：

```python
display_lidar_graph=True
```

可运行的示例见 `examples/example_display_lidar.py` 和 `examples/example_semantic_sensor.py`。


## 最小无人机控制器示例

下面是一个自定义无人机控制器的最小示例。
在 `src/swarm_rescue/solutions/` 目录中新建一个文件，例如 `my_great_drone.py`，并加入以下代码：

```python
from swarm_rescue.simulation.drone.drone_abstract import DroneAbstract

class MyGreatDrone(DroneAbstract):
    def control(self):
        # 每一步简单地向前移动
        return {
            "forward": 1.0,  # 全速前进
            "lateral": 0.0,  # 不横向移动
            "rotation": 0.0,  # 不旋转
            "grasper": 0      # 不抓取任何东西
        }

    def define_message_for_all(self) -> None:
        # 定义与其他无人机通信的消息内容
        pass
```

然后修改 `src/swarm_rescue/solutions/my_drone_eval.py` 以使用你的新无人机：
```python
from swarm_rescue.solutions.my_great_drone import MyGreatDrone
class MyDroneEval(MyGreatDrone):
    pass
```

现在，再次运行启动器，看看你的无人机如何行动！
```bash
python3 src/swarm_rescue/launcher.py
```

## 手动编辑救援炸弹（导入/导出）

为便于救援测试，你可以在 GUI 中手动编辑炸弹位置，并在之后将其作为 `bombs_file` 复用。

这样开始：

```bash
python3 src/swarm_rescue/launcher.py \
  -c config/competition_rescue_eval_plan.yml \
  --manual-bomb-edit \
  --manual-bombs-in path/to/input_bombs.json \
  --manual-bombs-out path/to/output_bombs.json
```

手动编辑模式下的操作：
- 左键单击：在鼠标位置添加一枚炸弹
- 右键单击：移除最近的炸弹
- `I`：从 `--manual-bombs-in` 导入炸弹（如已提供）
- `J`：把当前炸弹导出到 `--manual-bombs-out`（或默认文件名）
- `K`：清空所有炸弹
- `Enter`：确认布局并开始仿真

导出的 JSON 结构与现有炸弹文件相同：
`map_name`、`zones_config`、`bombs`。你之后可以直接通过评估 YAML 中的
`bombs_file` 或 `--bombs-file` 复用它。

# 项目结构概览

```
private-swarm-rescue/
├── src/
│   └── swarm_rescue/
│       ├── launcher.py
│       ├── solutions/
│       │   ├── my_drone_eval.py
│       │   ├── my_drone_lidar_communication.py
│       │   ├── my_drone_motionless.py
│       │   ├── my_drone_random.py
│       │   └── team_info.yml
│       ├── simulation/
│       │   ├── drone/
│       │   │   ├── drone_sensors.py
│       │   │   └── drone_abstract.py
│       │   ├── ray_sensors/
│       │   │   ├── drone_lidar.py
│       │   │   └── drone_semantic_sensor.py
│       │   ├── gui_map/
│       │   │   └── gui_sr.py
│       │   └── ...
│       ├── maps/
│       └── tools/
├── examples/
├── config/
├── tests/
├── INSTALL.md
├── README.md
└── pyproject.toml
```

# 联系方式

如果你对代码有疑问、想提出改进建议或报告 bug，可以联系：
emmanuel . battesti at ensta . fr
