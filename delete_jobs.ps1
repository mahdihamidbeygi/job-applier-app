# PowerShell script to delete job records from the database

# Database connection parameters
$DB_HOST = "localhost"
$DB_PORT = "5432"
$DB_NAME = "jobapplier"
$DB_USER = "mahdi"
$DB_PASS = "mahdi"

# Create connection string
$CONN_STRING = "host=$DB_HOST port=$DB_PORT dbname=$DB_NAME user=$DB_USER password=$DB_PASS"

# Function to execute SQL commands through psql
function Execute-SQL {
    param (
        [string]$SqlCommand
    )
    
    Write-Host "Executing SQL command: $SqlCommand"
    
    # Create a temporary SQL file
    $tempFile = [System.IO.Path]::GetTempFileName() + ".sql"
    Set-Content -Path $tempFile -Value $SqlCommand
    
    # Execute the SQL file using psql
    $result = & psql -h $DB_HOST -p $DB_PORT -d $DB_NAME -U $DB_USER -f $tempFile
    
    # Clean up the temporary file
    Remove-Item -Path $tempFile
    
    return $result
}

# Show the number of jobs currently in the database
Write-Host "Current job count in database:" -ForegroundColor Green
Execute-SQL 'SELECT COUNT(*) FROM "Job";'

# Ask for confirmation before deleting jobs
$confirmation = Read-Host "Do you want to delete all jobs? (y/n)"
if ($confirmation -eq 'y') {
    # First, delete related records from SavedJob and JobApplication tables due to foreign key constraints
    Write-Host "Deleting related records from SavedJob table..." -ForegroundColor Yellow
    Execute-SQL 'DELETE FROM "SavedJob" WHERE "jobId" IN (SELECT id FROM "Job");'
    
    Write-Host "Deleting related records from JobApplication table..." -ForegroundColor Yellow
    Execute-SQL 'DELETE FROM "JobApplication" WHERE "jobId" IN (SELECT id FROM "Job");'
    
    # Now delete the job records
    Write-Host "Deleting all job records from Job table..." -ForegroundColor Yellow
    Execute-SQL 'DELETE FROM "Job";'
    
    # Verify deletion
    Write-Host "Verifying job deletion:" -ForegroundColor Green
    Execute-SQL 'SELECT COUNT(*) FROM "Job";'
    
    Write-Host "Job deletion complete." -ForegroundColor Green
} else {
    Write-Host "Job deletion cancelled." -ForegroundColor Yellow
}

# Optional: Allow deleting jobs by platform
$deletePlatform = Read-Host "Do you want to delete jobs from a specific platform instead? (y/n)"
if ($deletePlatform -eq 'y') {
    $platform = Read-Host "Enter platform name (e.g., LinkedIn, Indeed, etc.)"
    
    # First, delete related records from SavedJob and JobApplication tables
    Write-Host "Deleting related records from SavedJob table for platform $platform..." -ForegroundColor Yellow
    Execute-SQL "DELETE FROM \"SavedJob\" WHERE \"jobId\" IN (SELECT id FROM \"Job\" WHERE platform = '$platform');"
    
    Write-Host "Deleting related records from JobApplication table for platform $platform..." -ForegroundColor Yellow
    Execute-SQL "DELETE FROM \"JobApplication\" WHERE \"jobId\" IN (SELECT id FROM \"Job\" WHERE platform = '$platform');"
    
    # Now delete the job records for the specified platform
    Write-Host "Deleting job records for platform $platform..." -ForegroundColor Yellow
    Execute-SQL "DELETE FROM \"Job\" WHERE platform = '$platform';"
    
    # Verify deletion
    Write-Host "Verifying job deletion:" -ForegroundColor Green
    Execute-SQL "SELECT platform, COUNT(*) FROM \"Job\" GROUP BY platform;"
    
    Write-Host "Platform-specific job deletion complete." -ForegroundColor Green
}

Write-Host "Script complete." -ForegroundColor Green 