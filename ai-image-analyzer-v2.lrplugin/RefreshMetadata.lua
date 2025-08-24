local LrApplication = import 'LrApplication'
local LrDialog = import 'LrDialog'
local LrTasks = import 'LrTasks'
local LrProgressScope = import 'LrProgressScope'

local function refreshMetadata()
    LrTasks.startAsyncTask(function()
        local catalog = LrApplication.activeCatalog()
        local selectedPhotos = catalog:getTargetPhotos()
        
        if not selectedPhotos or #selectedPhotos == 0 then
            LrDialog.message("No images selected", 
                "Please select the images you want to refresh metadata for.", 
                "info")
            return
        end
        
        local progressScope = LrProgressScope({
            title = "Refreshing metadata from XMP files...",
            functionContext = catalog,
        })
        
        progressScope:setPortionComplete(0, #selectedPhotos)
        
        catalog:withWriteAccessDo("Refresh AI Analyzer Metadata", function()
            for i, photo in ipairs(selectedPhotos) do
                progressScope:setPortionComplete(i - 1, #selectedPhotos)
                progressScope:setCaption("Processing: " .. (photo:getFormattedMetadata("fileName") or "Unknown"))
                
                -- Force Lightroom to re-read XMP metadata
                photo:readMetadata()
                
                if progressScope:isCanceled() then
                    break
                end
            end
        end)
        
        progressScope:done()
        
        if not progressScope:isCanceled() then
            LrDialog.message("Metadata Refresh Complete", 
                "Successfully refreshed metadata for " .. #selectedPhotos .. " image(s).\n\n" ..
                "The updated AI analysis data should now be visible in Lightroom's " ..
                "metadata panels and keyword lists.", 
                "info")
        end
    end)
end

refreshMetadata()
