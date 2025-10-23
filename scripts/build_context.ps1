param()

New-Item -ItemType Directory -Force -Path context | Out-Null

# repo tree (if tree is available for Windows; if not, ignore)
try {
  tree /F | Out-File -Encoding UTF8 context\repo_tree.txt
} catch {
  # Fallback: use dir command
  Get-ChildItem -Recurse -File | ForEach-Object { $_.FullName.Replace((Get-Location).Path + "\", "") } | Out-File -Encoding UTF8 context\repo_tree.txt
}

# last 200 commits
git log -n 200 --pretty="* %h %ad %an — %s" --date=short | Out-File -Encoding UTF8 context\commit_log.md

# hot files last 90 days
git log --since="90 days ago" --name-only --pretty=format:"" |
  Where-Object { $_ -ne "" } |
  Group-Object |
  Sort-Object Count -Descending |
  Select-Object -First 50 |
  ForEach-Object { "{0,4} {1}" -f $_.Count, $_.Name } |
  Out-File -Encoding UTF8 context\hot_files.md

# PR list (optional, requires 'gh' CLI)
try {
  $prs = gh pr list --limit 50 --json number,title,author,updatedAt | ConvertFrom-Json
  $lines = $prs | ForEach-Object { "* PR #$($_.number) $($_.title) by $($_.author.login) at $($_.updatedAt)" }
  $lines | Out-File -Encoding UTF8 context\pr_recent.md
} catch {
  # No GitHub CLI available
}

Write-Host "Context refreshed."
