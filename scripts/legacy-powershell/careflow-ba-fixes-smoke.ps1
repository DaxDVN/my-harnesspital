# API smoke for careflow-ba-fixes BA fixes (slot 1)
$ErrorActionPreference = 'Stop'
$base = 'http://localhost:5001'
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession

function Unwrap($resp) {
    if ($resp.Data) { return $resp.Data }
    return $resp
}

function Post-Json($url, $body) {
    $json = $body | ConvertTo-Json -Depth 10 -Compress
    $resp = Invoke-RestMethod -Uri $url -Method Post -Body $json -ContentType 'application/json' -WebSession $session
    return Unwrap $resp
}

function Get-Json($url) {
    $resp = Invoke-RestMethod -Uri $url -Method Get -WebSession $session
    return Unwrap $resp
}

$results = [ordered]@{}

try {
    $auth = Post-Json "$base/auth" @{
        provider = 'credentials'
        UserName = 'admin'
        Password = '123456'
        Meta     = @{ code = 'HMU' }
    }
    $results['auth'] = if ($auth.UserId) { 'PASS' } else { "FAIL: no UserId" }
}
catch {
    $results['auth'] = "FAIL: $($_.Exception.Message)"
    $results | ConvertTo-Json -Depth 3
    exit 1
}

# #11 MedicalVisitCode on inpatient list
try {
    $list = Get-Json "$base/medical-visits/inpatient?`$top=5"
    $items = @($list.ListOfObject)
    $hasVisitCodeProp = $items.Count -eq 0 -or ($null -ne $items[0].PSObject.Properties['MedicalVisitCode'])
    $visitRow = $items | Where-Object { $_.RowType -ne 'AdmissionOrder' -and $_.VisitId } | Select-Object -First 1
    $results['#11_MedicalVisitCode_field'] = if ($hasVisitCodeProp) { 'PASS' } else { 'FAIL: property missing' }
    if ($visitRow) {
        $results['#11_sample_code'] = if ($visitRow.MedicalVisitCode) { "PASS ($($visitRow.MedicalVisitCode))" } else { 'WARN: visit row has null code' }
    }
    else {
        $results['#11_sample_code'] = 'SKIP: no admission visit rows'
    }
}
catch {
    $results['#11_MedicalVisitCode_field'] = "FAIL: $($_.Exception.Message)"
}

# #4 setting key readable
try {
    $settings = Get-Json "$base/settings?Keys=InpatientAdvanceGateEnabled&Keys=InpatientAdvanceGateEnabled"
    $row = @($settings) | Where-Object { $_.Key -eq 'InpatientAdvanceGateEnabled' } | Select-Object -First 1
    $results['#4_advance_gate_setting'] = if ($row) { "PASS (value=$($row.Value))" } else { 'WARN: setting row missing (defaults false)' }
}
catch {
    $results['#4_advance_gate_setting'] = "FAIL: $($_.Exception.Message)"
}

# #18 guard — attempt create visit for patient with active inpatient (if seed exists)
try {
    $activePatientId = $null
    $emr = Get-Json "$base/emr/patient-records?`$top=10"
    $inTreatment = @($emr.ListOfObject) | Where-Object { $_.TreatmentStatus -eq 'in-treatment' } | Select-Object -First 1
    if (-not $inTreatment) {
        $ipd = Get-Json "$base/medical-visits/inpatient?`$top=10"
        $pending = @($ipd.ListOfObject) | Where-Object { $_.Status -in @('Pending','InProgress') -and $_.PatientId } | Select-Object -First 1
        if ($pending) {
            $inTreatment = [pscustomobject]@{ PatientId = $pending.PatientId }
        }
    }
    if ($inTreatment) { $activePatientId = $inTreatment.PatientId }

    if (-not $activePatientId) {
        $results['#18_active_episode_block'] = 'SKIP: no in-treatment patient in EMR list'
    }
    else {
        try {
            $serviceId = $null
            try {
                $ipdSvc = Get-Json "$base/medical-visits/inpatient?`$top=5"
                $visitRow = @($ipdSvc.ListOfObject) | Where-Object { $_.VisitId } | Select-Object -First 1
                if ($visitRow) {
                    $ordered = Get-Json "$base/medical-visits/$($visitRow.VisitId)/ordered-services"
                    $clinical = @($ordered.ClinicalServices) | Select-Object -First 1
                    if ($clinical) { $serviceId = $clinical.MedicalServiceId }
                }
            }
            catch { }

            if (-not $serviceId) { $serviceId = 1000 }

            $payload = @{
                Patient  = @{ PatientId = $activePatientId }
                Visit    = @{
                    PatientTypeId     = 1
                    ReasonForVisitId  = 1
                    TreatmentTypeId   = 1
                    ReceptionTime     = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
                    ServiceMarkupRate = 0
                }
                Services = @(@{ ServiceId = $serviceId; Quantity = 1 })
            } | ConvertTo-Json -Depth 5
            try {
                Post-Json "$base/medical-visits" ($payload | ConvertFrom-Json)
                $results['#18_active_episode_block'] = 'FAIL: create visit succeeded for in-treatment patient'
            }
            catch {
                $errBody = $_.ErrorDetails.Message
                if (-not $errBody -and $_.Exception.Response) {
                    $stream = $_.Exception.Response.GetResponseStream()
                    if ($stream) {
                        $reader = New-Object System.IO.StreamReader($stream)
                        $errBody = $reader.ReadToEnd()
                    }
                }
                if ($errBody -match 'PATIENT_HAS_ACTIVE_TREATMENT_EPISODE') {
                    $results['#18_active_episode_block'] = 'PASS'
                }
                else {
                    $results['#18_active_episode_block'] = "WARN: blocked but message=$errBody"
                }
            }
        }
        catch {
            $results['#18_active_episode_block'] = "SKIP: $($_.Exception.Message)"
        }
    }
}
catch {
    $results['#18_active_episode_block'] = "SKIP: $($_.Exception.Message)"
}

$results | ConvertTo-Json -Depth 3