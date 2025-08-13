local LrApplication = import 'LrApplication'
local LrDialogs = import 'LrDialogs'
local LrFileUtils = import 'LrFileUtils'
local LrPathUtils = import 'LrPathUtils'
local LrTasks = import 'LrTasks'

LrTasks.startAsyncTask(function()
    local catalog = LrApplication.activeCatalog()
    local targetPhotos = catalog:getTargetPhotos()
    
    if #targetPhotos == 0 then
        LrDialogs.message("No Selection", "Please select one or more images with AI analysis data to export.")
        return
    end
    
    -- Let user choose export location
    local result = LrDialogs.runSavePanel({
        title = "Export AI Analysis Report",
        label = "Save report as:",
        requiredFileType = "csv",
        initialDirectory = "~/Desktop",
        initialFileName = "AI_Analysis_Report.csv"
    })
    
    if not result then return end
    
    local reportPath = result
    
    -- Generate CSV report
    local csvContent = "Image Name,Path,AI Category,AI Subcategory,AI Score,AI Tags,AI Critique,Analysis Date,LR Rating\n"
    
    for _, photo in ipairs(targetPhotos) do
        local imageName = LrPathUtils.leafName(photo:getRawMetadata('path'))
        local imagePath = photo:getRawMetadata('path')
        local aiCategory = photo:getPropertyForPlugin(_PLUGIN, 'aiCategory') or ''
        local aiSubcategory = photo:getPropertyForPlugin(_PLUGIN, 'aiSubcategory') or ''
        local aiScore = photo:getPropertyForPlugin(_PLUGIN, 'aiScore') or ''
        local aiTags = photo:getPropertyForPlugin(_PLUGIN, 'aiTags') or ''
        local aiCritique = photo:getPropertyForPlugin(_PLUGIN, 'aiCritique') or ''
        local analysisDate = photo:getPropertyForPlugin(_PLUGIN, 'aiAnalysisDate') or ''
        local lrRating = photo:getRawMetadata('rating') or 0
        
        -- Escape CSV fields that contain commas or quotes
        local function escapeCsv(field)
            field = string.gsub(tostring(field), '"', '""')
            if string.find(field, '[,\n\r"]') then
                field = '"' .. field .. '"'
            end
            return field
        end
        
        csvContent = csvContent .. 
            escapeCsv(imageName) .. "," ..
            escapeCsv(imagePath) .. "," ..
            escapeCsv(aiCategory) .. "," ..
            escapeCsv(aiSubcategory) .. "," ..
            escapeCsv(aiScore) .. "," ..
            escapeCsv(aiTags) .. "," ..
            escapeCsv(aiCritique) .. "," ..
            escapeCsv(analysisDate) .. "," ..
            escapeCsv(lrRating) .. "\n"
    end
    
    -- Write the CSV file
    local file = io.open(reportPath, "w")
    if file then
        file:write(csvContent)
        file:close()
        
        LrDialogs.message(
            "Report Exported", 
            string.format("AI analysis report exported successfully to:\n%s\n\n%d images included in the report.", reportPath, #targetPhotos)
        )
    else
        LrDialogs.message("Export Failed", "Failed to write the report file. Please check the file path and permissions.")
    end
end)
