local LrBinding = import 'LrBinding'
local LrDate = import 'LrDate'

return {
    metadataFieldsForPhotos = function(photos)
        local f = {}
        
        -- AI analysis fields that will show in metadata panel
        f.aiAnalysisRating = {
            id = 'aiAnalysisRating',
            title = LOC "$$$/AI/Rating=AI Quality Rating",
            dataType = 'string',
            searchable = true,
            browsable = true,
            readOnly = true,
        }
        
        f.aiAnalysisDescription = {
            id = 'aiAnalysisDescription',
            title = LOC "$$$/AI/Description=AI Description", 
            dataType = 'string',
            searchable = true,
            browsable = true,
            readOnly = true,
        }
        
        f.aiAnalysisTags = {
            id = 'aiAnalysisTags',
            title = LOC "$$$/AI/Tags=AI Tags",
            dataType = 'string', 
            searchable = true,
            browsable = true,
            readOnly = true,
        }
        
        f.aiTechnicalScore = {
            id = 'aiTechnicalScore',
            title = LOC "$$$/AI/TechnicalScore=Technical Quality Score",
            dataType = 'string',
            searchable = true,
            browsable = true, 
            readOnly = true,
        }
        
        f.aiProcessingMode = {
            id = 'aiProcessingMode',
            title = LOC "$$$/AI/ProcessingMode=Processing Mode",
            dataType = 'string',
            searchable = true,
            browsable = true,
            readOnly = true,
        }
        
        f.aiProcessingDate = {
            id = 'aiProcessingDate', 
            title = LOC "$$$/AI/ProcessingDate=AI Processing Date",
            dataType = 'string',
            searchable = true,
            browsable = true,
            readOnly = true,
        }
        
        return f
    end,
    
    updateMetadataProvider = function(photo, metadataFieldsForPhotos)
        return {
            aiAnalysisRating = photo:getPropertyForPlugin(_PLUGIN, 'aiAnalysisRating') or "Not analyzed",
            aiAnalysisDescription = photo:getPropertyForPlugin(_PLUGIN, 'aiAnalysisDescription') or "Not analyzed",
            aiAnalysisTags = photo:getPropertyForPlugin(_PLUGIN, 'aiAnalysisTags') or "Not analyzed", 
            aiTechnicalScore = photo:getPropertyForPlugin(_PLUGIN, 'aiTechnicalScore') or "Not analyzed",
            aiProcessingMode = photo:getPropertyForPlugin(_PLUGIN, 'aiProcessingMode') or "None",
            aiProcessingDate = photo:getPropertyForPlugin(_PLUGIN, 'aiProcessingDate') or "Never",
        }
    end,
    
    schemaVersion = 1,
}
