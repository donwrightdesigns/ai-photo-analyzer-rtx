local LrApplication = import 'LrApplication'
local LrDialog = import 'LrDialog'
local LrTasks = import 'LrTasks'
local LrPathUtils = import 'LrPathUtils'
local LrFileUtils = import 'LrFileUtils'

local function archiveMode()
    LrTasks.startAsyncTask(function()
        local catalog = LrApplication.activeCatalog()
        local selectedPhotos = catalog:getTargetPhotos()
        
        if not selectedPhotos or #selectedPhotos == 0 then
            LrDialog.message("No images selected", 
                "Please select one or more images for Archive Mode processing.", 
                "info")
            return
        end
        
        -- Get image paths
        local imagePaths = {}
        for _, photo in ipairs(selectedPhotos) do
            local path = photo:getRawMetadata('path')
            if path then
                table.insert(imagePaths, path)
            end
        end
        
        if #imagePaths == 0 then
            LrDialog.message("No valid image paths", 
                "Unable to get file paths for selected images.", 
                "error")
            return
        end
        
        -- Create temporary file with image paths
        local tempDir = LrPathUtils.getStandardFilePath('temp')
        local tempFile = LrPathUtils.child(tempDir, "ai_analyzer_archive.txt")
        
        local file = io.open(tempFile, "w")
        if not file then
            LrDialog.message("Error", "Unable to create temporary file", "error")
            return
        end
        
        for _, path in ipairs(imagePaths) do
            file:write(path .. "\n")
        end
        file:close()
        
        -- Find desktop app
        local appPath = nil
        local possiblePaths = {
            "C:\\Program Files\\AI Image Analyzer\\ai_image_analyzer.exe",
            "C:\\Program Files (x86)\\AI Image Analyzer\\ai_image_analyzer.exe",
            LrPathUtils.child(LrPathUtils.parent(_PLUGIN.path), "ai_image_analyzer.exe"),
            LrPathUtils.child(LrPathUtils.parent(_PLUGIN.path), "main.py"),
        }
        
        for _, path in ipairs(possiblePaths) do
            local attr = LrFileUtils.fileAttributes(path)
            if attr then
                appPath = path
                break
            end
        end
        
        if not appPath then
            LrDialog.message("AI Image Analyzer not found", 
                "Please ensure the AI Image Analyzer desktop app is installed.", 
                "error")
            return
        end
        
        -- Launch with archive mode flag
        local command
        if string.match(appPath, "%.py$") then
            command = 'python "' .. appPath .. '" --mode archive --images "' .. tempFile .. '"'
        else
            command = '"' .. appPath .. '" --mode archive --images "' .. tempFile .. '"'
        end
        
        LrTasks.execute(command)
        
        LrDialog.message("Archive Mode Started", 
            "AI Image Analyzer is running in Archive Mode for " .. #imagePaths .. 
            " image(s).\n\nThis performs comprehensive analysis including:\n" ..
            "• AI tagging and descriptions\n" ..
            "• Technical metadata extraction\n" ..
            "• Searchable keyword generation\n\n" ..
            "Use 'Refresh Metadata from IPTC' when processing completes.",
            "info")
    end)
end

archiveMode()
