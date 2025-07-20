local LrBinding = import 'LrBinding'
local LrDialogs = import 'LrDialogs'
local LrFunctionContext = import 'LrFunctionContext'
local LrHttp = import 'LrHttp'
local LrPrefs = import 'LrPrefs'
local LrProgressScope = import 'LrProgressScope'
local LrTasks = import 'LrTasks'
local LrView = import 'LrView'
local JSON = require 'JSON'

local prefs = LrPrefs.prefsForPlugin()

-- Available models with descriptions
local AVAILABLE_MODELS = {
    { name = "llava:7b", title = "LLaVA 7B (Fast, 4GB)", description = "Lightweight model, faster processing, lower accuracy" },
    { name = "llava:13b", title = "LLaVA 13B (Balanced, 8GB)", description = "Recommended: Good balance of speed and accuracy" },
    { name = "llava:34b", title = "LLaVA 34B (Accurate, 20GB)", description = "High accuracy, slower processing, requires more RAM" },
}

local function getApiUrl()
    return prefs.apiUrl or "http://localhost:5000"
end

local function checkOllamaStatus()
    local response, headers = LrHttp.get(getApiUrl() .. "/api/model_status", {}, 5)
    
    if headers and headers.status == 200 then
        local result = JSON:decode(response)
        return result.success and result.ollama_running, result.models or {}
    end
    
    return false, {}
end

local function downloadModel(modelName)
    LrFunctionContext.callWithContext("downloadModel", function(context)
        local progressScope = LrProgressScope({
            title = "Downloading AI Model",
            functionContext = context,
        })
        
        progressScope:setCaption("Downloading " .. modelName .. "...")
        progressScope:setPortionComplete(0, 1)
        
        local postData = JSON:encode({
            model_name = modelName
        })
        
        -- Start download
        local response, headers = LrHttp.post(
            getApiUrl() .. "/api/download_model", 
            postData, 
            {
                { field = "Content-Type", value = "application/json" }
            },
            "POST",
            300  -- 5 minute timeout for model downloads
        )
        
        progressScope:setPortionComplete(1, 1)
        progressScope:done()
        
        if headers and headers.status == 200 then
            local result = JSON:decode(response)
            if result.success then
                LrDialogs.message(
                    "Download Complete", 
                    string.format("Model '%s' has been downloaded successfully and is ready to use.", modelName)
                )
            else
                LrDialogs.message(
                    "Download Failed", 
                    string.format("Failed to download model '%s': %s", modelName, result.error or "Unknown error")
                )
            end
        else
            LrDialogs.message(
                "Download Failed", 
                string.format("Failed to communicate with the AI service. Please ensure the web interface is running at %s", getApiUrl())
            )
        end
    end)
end

-- Main dialog function
LrFunctionContext.callWithContext("downloadModels", function(context)
    local viewFactory = LrView.osFactory()
    local properties = LrBinding.makePropertyTable(context)
    
    -- Check Ollama status
    local ollamaRunning, installedModels = checkOllamaStatus()
    
    if not ollamaRunning then
        LrDialogs.message(
            "Ollama Not Available",
            "The local AI service (Ollama) is not running or not available.\n\n" ..
            "Please ensure:\n" ..
            "1. Ollama is installed (download from https://ollama.ai)\n" ..
            "2. The AI Image Analyzer web service is running\n" ..
            "3. The web service URL is correct in Plugin Settings"
        )
        return
    end
    
    properties.selectedModel = "llava:13b"  -- Default selection
    
    -- Create installed models info
    local installedModelsText = "Currently Installed Models:\n"
    if #installedModels > 0 then
        for _, modelName in ipairs(installedModels) do
            installedModelsText = installedModelsText .. "• " .. modelName .. "\n"
        end
    else
        installedModelsText = installedModelsText .. "• None installed"
    end
    
    local contents = viewFactory:column {
        spacing = viewFactory:label_spacing(),
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Download Local AI Models",
                font = "<system/bold>",
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        viewFactory:row {
            viewFactory:static_text {
                title = installedModelsText,
                width_in_chars = 60,
                height_in_lines = math.max(3, #installedModels + 2),
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Select Model to Download:",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:radio_button {
                title = AVAILABLE_MODELS[1].title,
                value = LrBinding.bind("selectedModel"),
                checked_value = AVAILABLE_MODELS[1].name,
            },
        },
        viewFactory:row {
            viewFactory:static_text {
                title = "    " .. AVAILABLE_MODELS[1].description,
                width_in_chars = 60,
            },
        },
        
        viewFactory:row {
            viewFactory:radio_button {
                title = AVAILABLE_MODELS[2].title,
                value = LrBinding.bind("selectedModel"),
                checked_value = AVAILABLE_MODELS[2].name,
            },
        },
        viewFactory:row {
            viewFactory:static_text {
                title = "    " .. AVAILABLE_MODELS[2].description,
                width_in_chars = 60,
            },
        },
        
        viewFactory:row {
            viewFactory:radio_button {
                title = AVAILABLE_MODELS[3].title,
                value = LrBinding.bind("selectedModel"),
                checked_value = AVAILABLE_MODELS[3].name,
            },
        },
        viewFactory:row {
            viewFactory:static_text {
                title = "    " .. AVAILABLE_MODELS[3].description,
                width_in_chars = 60,
            },
        },
        
        viewFactory:separator { fill_horizontal = 1 },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "Download Requirements:",
                font = "<system/bold>",
            },
        },
        
        viewFactory:row {
            viewFactory:static_text {
                title = "• Stable internet connection\n• Adequate storage space (see model sizes above)\n• Sufficient RAM for model operation\n• Models will be cached locally for offline use",
                width_in_chars = 60,
                height_in_lines = 4,
            },
        },
    }
    
    local result = LrDialogs.presentModalDialog {
        title = "Download Local AI Models",
        contents = contents,
        actionVerb = "Download",
        cancelVerb = "Cancel",
    }
    
    if result == "ok" then
        local modelToDownload = properties.selectedModel
        
        -- Check if model is already installed
        for _, installedModel in ipairs(installedModels) do
            if installedModel == modelToDownload then
                local overwriteResult = LrDialogs.confirm(
                    "Model Already Installed",
                    string.format("The model '%s' is already installed. Do you want to re-download it?", modelToDownload),
                    "Re-download",
                    "Cancel"
                )
                if overwriteResult ~= "ok" then
                    return
                end
                break
            end
        end
        
        -- Confirm download
        local confirmResult = LrDialogs.confirm(
            "Confirm Download",
            string.format("Are you sure you want to download '%s'?\n\nThis may take several minutes depending on your internet connection.", modelToDownload),
            "Download",
            "Cancel"
        )
        
        if confirmResult == "ok" then
            LrTasks.startAsyncTask(function()
                downloadModel(modelToDownload)
            end)
        end
    end
end)
