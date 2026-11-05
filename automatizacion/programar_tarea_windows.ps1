# Programa el pipeline completo de ORCA en el Programador de tareas de Windows (mejora M1 del BPMN TO-BE).
# Ejecuta todos los días a las 02:00 (el temporizador del BPMN) el orquestador:
#   ingesta -> limpieza y quality gate -> banderas y score -> alertas -> retención
#
# Uso (PowerShell, desde la raíz del repositorio):
#   powershell -ExecutionPolicy Bypass -File automatizacion\programar_tarea_windows.ps1
# Para quitarla:
#   Unregister-ScheduledTask -TaskName "ORCA-Pipeline-Diario" -Confirm:$false
#
# La sal de seudonimización se define una sola vez como variable de usuario (no se versiona):
#   [Environment]::SetEnvironmentVariable("ORCA_SALT", "<valor secreto>", "User")

$repo   = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python).Source
$accion = New-ScheduledTaskAction -Execute $python `
          -Argument "notebooks\orquestar_pipeline.py --aplicar-retencion" -WorkingDirectory $repo
$disparador = New-ScheduledTaskTrigger -Daily -At 2:00am
$ajustes = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Hours 1) `
           -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName "ORCA-Pipeline-Diario" -Action $accion -Trigger $disparador -Settings $ajustes `
    -Description "ORCA: ingesta SECOP II, quality gate, score de riesgo y alertas (registro en automatizacion\registro_pipeline.csv)" -Force

Get-ScheduledTask -TaskName "ORCA-Pipeline-Diario" | Select-Object TaskName, State
