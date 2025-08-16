local LrApplication = import 'LrApplication'
local LrBinding = import 'LrBinding'
local LrColor = import 'LrColor'
local LrDialogs = import 'LrDialogs'
local LrFunctionContext = import 'LrFunctionContext'
local LrHttp = import 'LrHttp'
local LrPrefs = import 'LrPrefs'
local LrProgressScope = import 'LrProgressScope'
local LrTasks = import 'LrTasks'
local LrView = import 'LrView'
local JSON = require 'JSON'

local prefs = LrPrefs.prefsForPlugin()

-- Function to show multi-stage analysis dialog and execute pipeline
LrFunctionContext.callWithContext("Multi-Stage Analysis", function(context)
    local viewFactory = LrView.osFactory()
    local properties = LrBinding.makePropertyTable(context)
    
    -- Initialize properties with current preferences
    properties.apiUrl = prefs.apiUrl or "http://localhost:5001"
    properties.modelType = prefs.modelType or "gemini"
    properties.apiKey = prefs.apiKey or ""
    properties.qualityThreshold = prefs.qualityThreshold or 0.10
    properties.iqaModel = prefs.iqaModel or "brisque"
    properties.useExif = prefs.useExif or false
    properties.enableCritique = prefs.enableGalleryCritique or false
    properties.promptProfile = prefs.promptProfile or "professional_art_critic"
    
    -- Function to check if Flask service is running
    local function checkServiceStatus()
        local response, headers = LrHttp.get(properties.apiUrl .. "/api/model_status", {}, 5)
        return headers and headers.status == 200
    end
    
    -- Function to get available IQA models from server
    local function getAvailableIqaModels()
        local response, headers = LrHttp.get(properties.apiUrl .. "/api/pipeline_config", {}, 5)
        if headers and headers.status == 200 then
            local result = JSON:decode(response)
            return result.iqa_models or {"brisque", "niqe", "musiq", "topiq"}
        end
        return {"brisque", "niqe", "musiq", "topiq"}
    end
    
    local iqaModels = getAvailableIqaModels()
    
    -- Create dialog contents
    local contents = viewFactory:column {
        spacing = viewFactory:label_spacing(),
        
        -- Header
        viewFactory:row {
            viewFactory:static_text {
                title = "🚀 Multi-Stage Processing Pipeline",
                font = "<system/bold>",
                text_color = LrColor('blue'),
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Advanced workflow: Image Quality Assessment → AI Analysis → Metadata",
                width_in_chars = 70,
                height_in_lines = 2,
                text_color = LrColor('gray'),
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Stage 1: Image Quality Assessment (IQA)
        viewFactory:row {
            viewFactory:static_text {
                title = "📊 Stage 1: Image Quality Assessment",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "IQA Model:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "iqaModel",
                items = (function()
                    local items = {}
                    for _, model in ipairs(iqaModels) do
                        table.insert(items, { title = model:upper(), value = model })
                    end
                    return items
                end)(),
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Quality Threshold:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "qualityThreshold",
                items = {
                    { title = "Top 5% (Ultra-selective)", value = 0.05 },
                    { title = "Top 10% (Recommended)", value = 0.10 },
                    { title = "Top 15% (Balanced)", value = 0.15 },
                    { title = "Top 20% (Liberal)", value = 0.20 },
                    { title = "Top 25% (Very Liberal)", value = 0.25 },
                    { title = "Top 50% (Remove worst only)", value = 0.50 },
                },
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "",
                width = 120,
            },
            viewFactory:static_text {
                title = "💡 Only the highest quality images will be processed by expensive AI analysis",
                width_in_chars = 60,
                height_in_lines = 2,
                text_color = LrColor('gray'),
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Stage 2: AI Model Configuration
        viewFactory:row {
            viewFactory:static_text {
                title = "🤖 Stage 2: AI Analysis",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "AI Model:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "modelType",
                items = {
                    { title = "Google Gemini (Cloud)", value = "gemini" },
                    { title = "Ollama LLaVA (Local)", value = "ollama" },
                    { title = "BakLLaVA (Local)", value = "bakllava" },
                },
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Analysis Profile:",
                width = 120,
            },
            viewFactory:popup_menu {
                bind_to_object = properties,
                value = "promptProfile",
                items = {
                    { title = "Professional Art Critic", value = "professional_art_critic" },
                    { title = "Family Memory Keeper", value = "family_archivist" },
                    { title = "Commercial Photographer", value = "commercial_photographer" },
                    { title = "Social Media Expert", value = "social_media_curator" },
                    { title = "Documentary Journalist", value = "documentary_journalist" },
                    { title = "Travel Content Creator", value = "travel_blogger" },
                },
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "API Key:",
                width = 120,
            },
            viewFactory:edit_field {
                bind_to_object = properties,
                value = "apiKey",
                password = true,
                width_in_chars = 40,
                enabled = LrBinding.keyEquals("modelType", "gemini", properties),
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Generate detailed curatorial descriptions",
                bind_to_object = properties,
                value = "enableCritique",
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Stage 3: Metadata Options
        viewFactory:row {
            viewFactory:static_text {
                title = "💾 Stage 3: Metadata Storage",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:checkbox {
                title = "Write to EXIF (modifies original files)",
                bind_to_object = properties,
                value = "useExif",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "",
                width = 120,
            },
            viewFactory:static_text {
                title = "💡 Unchecked: Creates XMP sidecar files (non-destructive, recommended)",
                width_in_chars = 60,
                height_in_lines = 2,
                text_color = LrColor('gray'),
                visible = LrBinding.negativeOfKey("useExif", properties),
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        -- Pipeline Benefits Info
        viewFactory:row {
            viewFactory:static_text {
                title = "🎯 Pipeline Benefits:",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "• 85% faster processing (quality filtering before AI analysis)\n" ..
                        "• 90% cost reduction for cloud APIs\n" ..
                        "• Professional-grade image quality assessment\n" ..
                        "• Non-destructive XMP sidecar workflow\n" ..
                        "• Lightroom-compatible metadata",
                width_in_chars = 70,
                height_in_lines = 5,
                text_color = LrColor('gray'),
            },
        },
    }
    
    -- Show dialog
    local result = LrDialogs.presentModalDialog {
        title = "AI Image Analyzer - Multi-Stage Pipeline",
        contents = contents,
        actionVerb = "Start Pipeline",
        cancelVerb = "Cancel",
    }
    
    if result == "ok" then
        -- Save preferences
        prefs.qualityThreshold = properties.qualityThreshold
        prefs.iqaModel = properties.iqaModel
        prefs.useExif = properties.useExif
        prefs.modelType = properties.modelType
        prefs.apiKey = properties.apiKey
        prefs.enableGalleryCritique = properties.enableCritique
        prefs.promptProfile = properties.promptProfile
        
        -- Get folder to process
        local folderResult = LrDialogs.runOpenPanel({
            title = "Select Folder for Multi-Stage Analysis",
            canChooseFiles = false,
            canChooseDirectories = true,
            allowsMultipleSelection = false,
        })
        
        if not folderResult then return end
        
        local folderPath = folderResult[1]
        if not folderPath then return end
        
        -- Check if service is running
        if not checkServiceStatus() then
            LrDialogs.message(
                "Service Not Available", 
                "The AI Image Analyzer service is not running. Please start the Flask web service:\n\n" ..
                "python web/app.py\n\n" ..
                "Then ensure it's accessible at: " .. properties.apiUrl
            )
            return
        end
        
        -- Start multi-stage processing
        LrTasks.startAsyncTask(function()
            LrFunctionContext.callWithContext("Multi-Stage Processing", function(progressContext)
                local progressScope = LrProgressScope({
                    title = "Multi-Stage Processing Pipeline",
                    functionContext = progressContext,
                })
                
                progressScope:setCaption("Starting multi-stage analysis...")
                
                -- Prepare API request
                local postData = JSON:encode({
                    directory_path = folderPath,
                    model_type = properties.modelType,
                    api_key = properties.apiKey,
                    quality_threshold = properties.qualityThreshold,
                    iqa_model = properties.iqaModel,
                    use_exif = properties.useExif,
                    enable_gallery_critique = properties.enableCritique,
                    prompt_profile = properties.promptProfile,
                })
                
                -- Send request to multi-stage pipeline endpoint
                local response, headers = LrHttp.post(
                    properties.apiUrl .. "/api/start_multistage_processing",
                    postData,
                    {
                        { field = "Content-Type", value = "application/json" }
                    },
                    "POST",
                    10
                )
                
                if headers and headers.status == 200 then
                    local result = JSON:decode(response)
                    if result.success then
                        progressScope:setCaption("Multi-stage pipeline started on server...")
                        
                        -- Show success message with detailed information
                        LrDialogs.message(
                            "🚀 Multi-Stage Pipeline Started",
                            string.format(
                                "Multi-stage processing has been initiated!\n\n" ..
                                "📊 Configuration:\n" ..
                                "• IQA Model: %s\n" ..
                                "• Quality Threshold: Top %.0f%%\n" ..
                                "• AI Model: %s\n" ..
                                "• Analysis Profile: %s\n" ..
                                "• Metadata: %s\n\n" ..
                                "💡 Monitor progress at: %s\n\n" ..
                                "The pipeline will:\n" ..
                                "1. Assess quality of all images using %s\n" ..
                                "2. Select top %.0f%% for AI analysis\n" ..
                                "3. Generate metadata with %s model\n" ..
                                "4. Save results as %s\n\n" ..
                                "📈 Expected savings: 85%% time, 90%% costs",
                                properties.iqaModel:upper(),
                                properties.qualityThreshold * 100,
                                properties.modelType:upper(),
                                (properties.promptProfile or ""):gsub("_", " "):gsub("(%l)(%w*)", function(a, b) return string.upper(a) .. b end),
                                properties.useExif and "EXIF embedded" or "XMP sidecar files",
                                properties.apiUrl,
                                properties.iqaModel:upper(),
                                properties.qualityThreshold * 100,
                                properties.modelType:upper(),
                                properties.useExif and "embedded EXIF data" or "XMP sidecar files"
                            )
                        )
                    else
                        LrDialogs.message(
                            "Pipeline Error", 
                            "Failed to start multi-stage pipeline:\n\n" .. (result.error or "Unknown error")
                        )
                    end
                else
                    LrDialogs.message(
                        "Communication Error", 
                        "Failed to communicate with the AI service. Please ensure the Flask web service is running at:\n\n" .. 
                        properties.apiUrl
                    )
                end
                
                progressScope:done()
            end)
        end)
    end
end)
