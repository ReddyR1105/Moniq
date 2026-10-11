param([string]$Directory = $PSScriptRoot)
$ErrorActionPreference = 'Stop'
$presentationApp = New-Object -ComObject PowerPoint.Application
try {
    foreach ($name in @('Moniq_Hacklanta_2026_Pitch', 'Moniq_Technical_Backup')) {
        $source = Join-Path $Directory ($name + '.pptx')
        $deck = $presentationApp.Presentations.Open($source, -1, 0, 0)
        try {
            $deck.SaveAs((Join-Path $Directory ($name + '.pdf')), 32)
            $previewPath = Join-Path $Directory $(if ($name -eq 'Moniq_Hacklanta_2026_Pitch') {'slide-previews'} else {'backup-previews'})
            New-Item -ItemType Directory -Path $previewPath -Force | Out-Null
            for ($i = 1; $i -le $deck.Slides.Count; $i++) {
                $slidePath = Join-Path $previewPath ('slide-{0:D2}.png' -f $i)
                $deck.Slides.Item($i).Export($slidePath, 'PNG', 1920, 1080)
            }
            $report = @()
            foreach ($page in $deck.Slides) {
                foreach ($shape in $page.Shapes) {
                    if ($shape.HasTextFrame -eq -1 -and $shape.TextFrame.HasText -eq -1) {
                        $tf = $shape.TextFrame2
                        $report += [pscustomobject]@{
                            slide = $page.SlideIndex
                            text = $shape.TextFrame.TextRange.Text
                            boxHeight = $shape.Height
                            textHeight = $tf.TextRange.BoundHeight
                            boxWidth = $shape.Width
                            textWidth = $tf.TextRange.BoundWidth
                        }
                    }
                }
            }
            $report | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $Directory ($name + '-text-bounds.json')) -Encoding UTF8
            Write-Output ('Exported ' + $name + ': ' + $deck.Slides.Count + ' slides, PDF, native PowerPoint previews')
        } finally { $deck.Close() }
    }
} finally { $presentationApp.Quit() }
