local LrApplication = import 'LrApplication'
local LrDialog = import 'LrDialog'
local LrFunctionContext = import 'LrFunctionContext'
local LrTasks = import 'LrTasks'
local LrPathUtils = import 'LrPathUtils'
local LrFileUtils = import 'LrFileUtils'
local LrShell = import 'LrShell'

local function sendToAnalyzer()
    LrTasks.startAsyncTask(function()
        local catalog = LrApplication.activeCatalog()
        local selectedPhotos = catalog:getTargetPhotos()
        
        if not selectedPhotos or #selectedPhotos == 0 then
            LrDialog.message("No images selected", 
                "Please select one or more images in the Library module before running AI Image Analyzer.", 
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
        local tempFile = LrPathUtils.child(tempDir, "ai_analyzer_images.txt")
        
        local file = io.open(tempFile, "w")
        if not file then
            LrDialog.message("Error", "Unable to create temporary file", "error")
            return
        end
        
        for _, path in ipairs(imagePaths) do
            file:write(path .. "\n")
        end
        file:close()
        
        -- Find and launch the desktop app
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
                "Please ensure the AI Image Analyzer desktop app is installed.\n\n" ..
                "Looking for:\n" ..
                "• C:\\Program Files\\AI Image Analyzer\\ai_image_analyzer.exe\n" ..
                "• main.py in the plugin directory", 
                "error")
            return
        end
        
        -- Launch the desktop app with image list
        local command
        if string.match(appPath, "%.py$") then
            -- Python script
            command = 'python "' .. appPath .. '" --images "' .. tempFile .. '"'
        else
            -- Executable
            command = '"' .. appPath .. '" --images "' .. tempFile .. '"'
        end
        
        LrTasks.execute(command)
        
        LrDialog.message("AI Image Analyzer Launched", 
            "The AI Image Analyzer desktop app has been launched with " .. 
            #imagePaths .. " selected image(s).\n\n" ..
            "After processing is complete, use 'Refresh Metadata from XMP' " ..
            "to update Lightroom with the new analysis data.", 
            "info")
    end)
end

sendToAnalyzer()
