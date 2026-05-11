param(
    # Linux 板子的主机名或者 IP。
    [Parameter(Mandatory = $true)]
    [string]$Host,

    # 板子上的 SSH 用户名。
    [Parameter(Mandatory = $true)]
    [string]$User,

    # 板子上接收项目目录的根路径。
    [string]$RemoteRoot = "/opt/car-control",

    # 跳过在板子上编译 C++ 桥接层。
    [switch]$SkipBridgeBuild,

    # 部署后跑一个很短的 mock 烟雾测试。
    [switch]$SmokeTest = $false,

    # 板子上的 Python 可执行文件名。
    [string]$RemotePython = "python3",

    # 运行时选择控制挡位。
    [ValidateSet("conservative", "normal", "sport")]
    [string]$ControlProfile = "normal"
)

$ErrorActionPreference = "Stop"

function Assert-CommandExists {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command not found: $Name"
    }
}

function Join-RemotePath {
    param(
        [string]$Parent,
        [string]$Child
    )

    if ($Parent.EndsWith("/")) {
        return "$Parent$Child"
    }
    return "$Parent/$Child"
}

function Copy-Path {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path $Source)) {
        throw "Missing source path: $Source"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
}

Assert-CommandExists ssh
Assert-CommandExists scp

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDir "..")).Path

$stageRoot = Join-Path $env:TEMP ("car_control_system_deploy_" + [guid]::NewGuid().ToString("N"))
$stageProject = Join-Path $stageRoot "car_control_system"

New-Item -ItemType Directory -Force -Path $stageProject | Out-Null

# 只复制运行所需的部分和桥接入口，保持部署包尽量小。
Copy-Path -Source (Join-Path $projectRoot "app") -Destination (Join-Path $stageProject "app")
Copy-Path -Source (Join-Path $projectRoot "bridge") -Destination (Join-Path $stageProject "bridge")
Copy-Path -Source (Join-Path $projectRoot "car_control") -Destination (Join-Path $stageProject "car_control")
Copy-Path -Source (Join-Path $projectRoot "configs") -Destination (Join-Path $stageProject "configs")
Copy-Path -Source (Join-Path $projectRoot "scripts") -Destination (Join-Path $stageProject "scripts")
Copy-Path -Source (Join-Path $projectRoot "vendor") -Destination (Join-Path $stageProject "vendor")
Copy-Path -Source (Join-Path $projectRoot "car_control_system.py") -Destination (Join-Path $stageProject "car_control_system.py")
Copy-Path -Source (Join-Path $projectRoot "remote_control_sender.py") -Destination (Join-Path $stageProject "remote_control_sender.py")
Copy-Path -Source (Join-Path $projectRoot "README.md") -Destination (Join-Path $stageProject "README.md")
Copy-Path -Source (Join-Path $projectRoot "docs") -Destination (Join-Path $stageProject "docs")
Copy-Path -Source (Join-Path $projectRoot "tests") -Destination (Join-Path $stageProject "tests")

Get-ChildItem -Path $stageRoot -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Path $stageRoot -Recurse -File -Filter "*.pyc" | Remove-Item -Force
$bridgeBuildDir = Join-Path $stageProject "bridge\cpp\build"
if (Test-Path $bridgeBuildDir) {
    Remove-Item -LiteralPath $bridgeBuildDir -Recurse -Force
}

try {
    $remoteProjectRoot = Join-RemotePath -Parent $RemoteRoot -Child "car_control_system"

    # 先在目标机器上准备根目录。
    & ssh "$User@$Host" "mkdir -p '$RemoteRoot'"

    # 以单个项目目录上传，方便整体替换和归档。
    & scp -r "$stageProject" "$User@$Host:$RemoteRoot/"

    if (-not $SkipBridgeBuild) {
        $remoteBridgeDir = Join-RemotePath -Parent $remoteProjectRoot -Child "bridge/cpp"
        $buildCommand = @"
cd '$remoteBridgeDir' && cmake -S . -B build && cmake --build build -j\$(nproc)
"@
        & ssh "$User@$Host" $buildCommand
    }

    if ($SmokeTest) {
        $smokeCommand = @"
cd '$remoteProjectRoot' && $RemotePython car_control_system.py --mock --input demo --control-profile $ControlProfile --max-loops 3
"@
        & ssh "$User@$Host" $smokeCommand
    }
}
finally {
    if (Test-Path $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force
    }
}
