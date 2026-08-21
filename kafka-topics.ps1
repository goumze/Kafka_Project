param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('Create', 'List', 'Describe')]
    [string]$Action,

    [Parameter(Mandatory = $false, Position = 1)]
    [string]$TopicName,

    [Parameter(Mandatory = $false)]
    [int]$Partitions = 1,

    [Parameter(Mandatory = $false)]
    [int]$ReplicationFactor = 3
)

function Invoke-KafkaCommand {
    param(
        [string]$Arguments
    )
    # Use the broker's internal Docker network address instead of localhost.
    $bootstrap = "kafka1:9092"
    # Use docker compose exec to reference the service name reliably.
    $dockerCmd = "docker compose exec -T kafka1 kafka-topics --bootstrap-server $bootstrap $Arguments"
    Write-Host "Executing: $dockerCmd" -ForegroundColor Cyan
    $output = & cmd /c $dockerCmd 2>&1
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 0) {
        Write-Host $output -ForegroundColor Green
    } else {
        Write-Host "Error (exit code $exitCode):" -ForegroundColor Red
        Write-Host $output -ForegroundColor Red
    }
    return $exitCode
}

switch ($Action) {
    'Create' {
        if (-not $TopicName) {
            Write-Error "-TopicName is required for Create action."
            exit 1
        }
        $args = "--create --topic $TopicName --partitions $Partitions --replication-factor $ReplicationFactor"
        $code = Invoke-KafkaCommand -Arguments $args
        if ($code -eq 0) { Write-Host "Topic '$TopicName' created successfully." -ForegroundColor Green }
        exit $code
    }
    'List' {
        $args = "--list"
        $code = Invoke-KafkaCommand -Arguments $args
        exit $code
    }
    'Describe' {
        if (-not $TopicName) {
            Write-Error "-TopicName is required for Describe action."
            exit 1
        }
        $args = "--describe --topic $TopicName"
        $code = Invoke-KafkaCommand -Arguments $args
        exit $code
    }
    default {
        Write-Error "Unsupported action: $Action"
        exit 1
    }
}
