local LrApplication = import 'LrApplication'
local LrBinding = import 'LrBinding'
local LrDate = import 'LrDate'
local LrDialogs = import 'LrDialogs'
local LrFileUtils = import 'LrFileUtils'
local LrFunctionContext = import 'LrFunctionContext'
local LrHttp = import 'LrHttp'
local LrPathUtils = import 'LrPathUtils'
local LrProgressScope = import 'LrProgressScope'
local LrTasks = import 'LrTasks'
local JSON = require 'JSON'

local AIImageAnalyzer = {}

-- Configuration
local API_BASE_URL = "http://localhost:5000"
local TIMEOUT = 120

-- Helper function to get plugin preferences
local function getPreferences()
    local prefs = import 'LrPrefs'.prefsForPlugin()
    return {
        apiUrl = prefs.apiUrl or API_BASE_URL,
        writeExif = prefs.writeExif or true,
        timeout = prefs.timeout or TIMEOUT,
        modelType = prefs.modelType or "llava",
        apiKey = prefs.apiKey or "",
        enableGalleryCritique = prefs.enableGalleryCritique or false,
        generateXmp = prefs.generateXmp or false,
        critiqueThreshold = prefs.critiqueThreshold or 5,
    }
end

-- Helper function to parse EXIF data from image
local function parseExifAnalysis(photo)
    local exifData = photo:getRawMetadata('exif')
    if not exifData then return nil end
    
    -- Try to extract analysis data from EXIF UserComment
    local userComment = exifData['UserComment']
    if userComment and string.find(userComment, "Critique:") then
        local analysis = {}
        
        -- Parse the structured comment
        analysis.critique = string.match(userComment, "Critique: ([^|]*)")
        analysis.score = string.match(userComment, "Score: ([^/]*)")
        analysis.tags = string.match(userComment, "Tags: ([^|]*)")
        
        -- Try to get category from ImageDescription
        local description = exifData['ImageDescription']
        if description then
            analysis.category = string.match(description, "Category: ([^,]*)")
            analysis.subcategory = string.match(description, "Subcategory: ([^,]*)")
        end
        
        -- Get rating
        analysis.rating = exifData['Rating'] or 0
        
        return analysis
    end
    
    return nil
end

-- Function to check if Flask service is running
local function checkServiceStatus()
    local prefs = getPreferences()
    local response, headers = LrHttp.get(prefs.apiUrl .. "/api/model_status", {}, 5)
    
    if headers and headers.status == 200 then
        local result = JSON:decode(response)
        return result.success and result.ollama_running and result.llava_available
    end
    
    return false
end

-- Function to analyze a single image via API
local function analyzeImageViaAPI(imagePath, prefs)
    local postData = JSON:encode({
        image_path = imagePath,
        write_exif = prefs.writeExif,
        model_type = prefs.modelType,
        api_key = prefs.apiKey
    })
    
    local response, headers = LrHttp.post(
        prefs.apiUrl .. "/api/analyze_single", 
        postData, 
        {
            { field = "Content-Type", value = "application/json" }
        },
        "POST",
        prefs.timeout
    )
    
    if headers and headers.status == 200 then
        return JSON:decode(response)
    end
    
    return nil
end

-- Function to update Lightroom metadata with analysis results
local function updatePhotoMetadata(photo, analysis)
    if not analysis then return end
    
    local catalog = LrApplication.activeCatalog()
    
    catalog:withWriteAccessDo("Update AI Analysis", function()
        photo:setPropertyForPlugin(_PLUGIN, 'aiCategory', analysis.category or '')
        photo:setPropertyForPlugin(_PLUGIN, 'aiSubcategory', analysis.subcategory or '')
        photo:setPropertyForPlugin(_PLUGIN, 'aiScore', tostring(analysis.score or 0) .. "/10")
        photo:setPropertyForPlugin(_PLUGIN, 'aiTags', table.concat(analysis.tags or {}, ", "))
        photo:setPropertyForPlugin(_PLUGIN, 'aiCritique', analysis.critique or '')
        photo:setPropertyForPlugin(_PLUGIN, 'aiAnalysisDate', LrDate.timeToUserFormat(LrDate.currentTime()))
        
        -- Set Lightroom rating based on AI score
        if analysis.score then
            local rating = math.min(5, math.max(1, math.ceil(analysis.score / 2)))
            photo:setRawMetadata('rating', rating)
        end
        
        -- Add tags to Lightroom keywords
        if analysis.tags and #analysis.tags > 0 then
            local keywords = photo:getRawMetadata('keywords') or {}
            for _, tag in ipairs(analysis.tags) do
                table.insert(keywords, tag)
            end
            photo:setRawMetadata('keywords', keywords)
        end
    end)
end

-- Function to load existing analysis from EXIF
function AIImageAnalyzer.loadExistingAnalysis(photo)
    local analysis = parseExifAnalysis(photo)
    if analysis then
        updatePhotoMetadata(photo, analysis)
    end
end

-- Function to analyze selected images
function AIImageAnalyzer.analyzeSelectedImages()
    LrFunctionContext.callWithContext("analyzeSelectedImages", function(context)
        local catalog = LrApplication.activeCatalog()
        local targetPhotos = catalog:getTargetPhotos()
        
        if #targetPhotos == 0 then
            LrDialogs.message("No Selection", "Please select one or more images to analyze.")
            return
        end
        
        -- Check if service is running
        if not checkServiceStatus() then
            local result = LrDialogs.confirm(
                "Service Not Available",
                "The AI Image Analyzer service is not running or not available. Would you like to try loading existing analysis from EXIF data instead?",
                "Load EXIF Data",
                "Cancel"
            )
            
            if result == "ok" then
                for _, photo in ipairs(targetPhotos) do
                    AIImageAnalyzer.loadExistingAnalysis(photo)
                end
            end
            return
        end
        
        local prefs = getPreferences()
        local progressScope = LrProgressScope({
            title = "Analyzing Images with AI",
            functionContext = context,
        })
        
        progressScope:setPortionComplete(0, #targetPhotos)
        
        for i, photo in ipairs(targetPhotos) do
            if progressScope:isCanceled() then break end
            
            local imagePath = photo:getRawMetadata('path')
            progressScope:setPortionComplete(i - 1, #targetPhotos)
            progressScope:setCaption("Analyzing " .. LrPathUtils.leafName(imagePath))
            
            -- Try to analyze via API
            local analysisResult = analyzeImageViaAPI(imagePath, prefs)
            
            if analysisResult and analysisResult.success then
                updatePhotoMetadata(photo, analysisResult.analysis)
            else
                -- Fallback to EXIF data
                AIImageAnalyzer.loadExistingAnalysis(photo)
            end
            
            LrTasks.sleep(0.1) -- Small delay to prevent overwhelming the service
        end
        
        progressScope:done()
        
        LrDialogs.message(
            "Analysis Complete", 
            string.format("Analyzed %d images successfully.", #targetPhotos)
        )
    end)
end

-- Function to batch analyze a folder
function AIImageAnalyzer.batchAnalyzeFolder()
    LrFunctionContext.callWithContext("batchAnalyzeFolder", function(context)
        local result = LrDialogs.runOpenPanel({
            title = "Select Folder to Analyze",
            canChooseFiles = false,
            canChooseDirectories = true,
            allowsMultipleSelection = false,
        })
        
        if not result then return end
        
        local folderPath = result[1]
        if not folderPath then return end
        
        -- Check if service is running
        if not checkServiceStatus() then
            LrDialogs.message("Service Not Available", "The AI Image Analyzer service is not running or not available.")
            return
        end
        
        local prefs = getPreferences()
        local progressScope = LrProgressScope({
            title = "Batch Analyzing Folder",
            functionContext = context,
        })
        
        progressScope:setCaption("Starting batch analysis...")
        
        -- Send batch analysis request to Flask service
        local postData = JSON:encode({
            directory_path = folderPath,
            write_exif = prefs.writeExif,
            model_type = prefs.modelType,
            api_key = prefs.apiKey
        })
        
        local response, headers = LrHttp.post(
            prefs.apiUrl .. "/api/start_processing", 
            postData, 
            {
                { field = "Content-Type", value = "application/json" }
            },
            "POST",
            5
        )
        
        if headers and headers.status == 200 then
            local result = JSON:decode(response)
            if result.success then
                progressScope:setCaption("Batch analysis started on server. Check the web interface for progress.")
                LrDialogs.message(
                    "Batch Analysis Started",
                    "Batch analysis has been started on the server. You can monitor progress at " .. prefs.apiUrl
                )
            else
                LrDialogs.message("Error", "Failed to start batch analysis: " .. (result.error or "Unknown error"))
            end
        else
            LrDialogs.message("Error", "Failed to communicate with the AI service.")
        end
        
        progressScope:done()
    end)
end

-- Function to clear analysis data
function AIImageAnalyzer.clearAnalysis()
    local catalog = LrApplication.activeCatalog()
    local targetPhotos = catalog:getTargetPhotos()
    
    if #targetPhotos == 0 then
        LrDialogs.message("No Selection", "Please select one or more images to clear analysis data.")
        return
    end
    
    local result = LrDialogs.confirm(
        "Clear Analysis Data",
        string.format("Are you sure you want to clear AI analysis data for %d selected images?", #targetPhotos),
        "Clear Data",
        "Cancel"
    )
    
    if result == "ok" then
        catalog:withWriteAccessDo("Clear AI Analysis", function()
            for _, photo in ipairs(targetPhotos) do
                photo:setPropertyForPlugin(_PLUGIN, 'aiCategory', '')
                photo:setPropertyForPlugin(_PLUGIN, 'aiSubcategory', '')
                photo:setPropertyForPlugin(_PLUGIN, 'aiScore', '')
                photo:setPropertyForPlugin(_PLUGIN, 'aiTags', '')
                photo:setPropertyForPlugin(_PLUGIN, 'aiCritique', '')
                photo:setPropertyForPlugin(_PLUGIN, 'aiAnalysisDate', '')
            end
        end)
        
        LrDialogs.message("Analysis Cleared", "AI analysis data has been cleared from selected images.")
    end
end

-- Function to view analysis results
function AIImageAnalyzer.viewAnalysis()
    local catalog = LrApplication.activeCatalog()
    local targetPhotos = catalog:getTargetPhotos()
    
    if #targetPhotos == 0 then
        LrDialogs.message("No Selection", "Please select an image to view its analysis.")
        return
    end
    
    local photo = targetPhotos[1]
    local category = photo:getPropertyForPlugin(_PLUGIN, 'aiCategory') or 'Not analyzed'
    local subcategory = photo:getPropertyForPlugin(_PLUGIN, 'aiSubcategory') or ''
    local score = photo:getPropertyForPlugin(_PLUGIN, 'aiScore') or ''
    local tags = photo:getPropertyForPlugin(_PLUGIN, 'aiTags') or ''
    local critique = photo:getPropertyForPlugin(_PLUGIN, 'aiCritique') or ''
    local analysisDate = photo:getPropertyForPlugin(_PLUGIN, 'aiAnalysisDate') or ''
    
    local message = string.format(
        "AI Analysis for: %s\n\n" ..
        "Category: %s\n" ..
        "Subcategory: %s\n" ..
        "Quality Score: %s\n" ..
        "Tags: %s\n\n" ..
        "Critique: %s\n\n" ..
        "Analysis Date: %s",
        LrPathUtils.leafName(photo:getRawMetadata('path')),
        category, subcategory, score, tags, critique, analysisDate
    )
    
    LrDialogs.message("AI Analysis Results", message)
end

return AIImageAnalyzer
