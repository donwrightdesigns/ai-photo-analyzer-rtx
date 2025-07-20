local LrBinding = import 'LrBinding'
local LrDate = import 'LrDate'
local LrDialogs = import 'LrDialogs'
local LrFileUtils = import 'LrFileUtils'
local LrPathUtils = import 'LrPathUtils'
local LrView = import 'LrView'

local AIImageAnalyzer = require 'AIImageAnalyzerAPI'

return {
    metadataFieldsForPhotos = {
        {
            id = 'aiCategory',
            title = 'AI Category',
            dataType = 'string',
            searchable = true,
            browsable = true,
        },
        {
            id = 'aiSubcategory',
            title = 'AI Subcategory',
            dataType = 'string',
            searchable = true,
            browsable = true,
        },
        {
            id = 'aiScore',
            title = 'AI Quality Score',
            dataType = 'string',
            searchable = true,
            browsable = true,
        },
        {
            id = 'aiTags',
            title = 'AI Tags',
            dataType = 'string',
            searchable = true,
            browsable = true,
        },
        {
            id = 'aiCritique',
            title = 'AI Critique',
            dataType = 'string',
            searchable = false,
            browsable = false,
        },
        {
            id = 'aiAnalysisDate',
            title = 'AI Analysis Date',
            dataType = 'string',
            searchable = true,
            browsable = true,
        },
    },

    schemaVersion = 1,

    updateFromEarlierSchemaVersion = function( catalog, previousSchemaVersion )
        -- Handle schema updates if needed
    end,

    startDialog = function( propertyTable )
        -- Initialize property table if needed
    end,

    sectionsForTopOfDialog = function( viewFactory, propertyTable )
        return {
            {
                title = 'AI Image Analysis',
                
                viewFactory:row {
                    spacing = viewFactory:label_spacing(),
                    
                    viewFactory:static_text {
                        title = 'Category:',
                        width = 80,
                    },
                    
                    viewFactory:static_text {
                        title = LrBinding.bind( 'aiCategory' ),
                        text_color = LrColor( 'blue' ),
                    },
                },
                
                viewFactory:row {
                    spacing = viewFactory:label_spacing(),
                    
                    viewFactory:static_text {
                        title = 'Subcategory:',
                        width = 80,
                    },
                    
                    viewFactory:static_text {
                        title = LrBinding.bind( 'aiSubcategory' ),
                    },
                },
                
                viewFactory:row {
                    spacing = viewFactory:label_spacing(),
                    
                    viewFactory:static_text {
                        title = 'Quality Score:',
                        width = 80,
                    },
                    
                    viewFactory:static_text {
                        title = LrBinding.bind( 'aiScore' ),
                        text_color = LrColor( 'orange' ),
                    },
                },
                
                viewFactory:row {
                    spacing = viewFactory:label_spacing(),
                    
                    viewFactory:static_text {
                        title = 'Tags:',
                        width = 80,
                    },
                    
                    viewFactory:static_text {
                        title = LrBinding.bind( 'aiTags' ),
                        width_in_chars = 40,
                        height_in_lines = 2,
                    },
                },
                
                viewFactory:row {
                    spacing = viewFactory:label_spacing(),
                    
                    viewFactory:static_text {
                        title = 'Critique:',
                        width = 80,
                    },
                    
                    viewFactory:static_text {
                        title = LrBinding.bind( 'aiCritique' ),
                        width_in_chars = 50,
                        height_in_lines = 4,
                        selectable = true,
                    },
                },
                
                viewFactory:row {
                    spacing = viewFactory:label_spacing(),
                    
                    viewFactory:static_text {
                        title = 'Analysis Date:',
                        width = 80,
                    },
                    
                    viewFactory:static_text {
                        title = LrBinding.bind( 'aiAnalysisDate' ),
                        text_color = LrColor( 'gray' ),
                    },
                },
                
                viewFactory:separator { fill_horizontal = 1 },
                
                viewFactory:row {
                    spacing = viewFactory:label_spacing(),
                    
                    viewFactory:push_button {
                        title = 'Analyze This Image',
                        action = function()
                            AIImageAnalyzer.analyzeSelectedImages()
                        end,
                    },
                    
                    viewFactory:push_button {
                        title = 'Clear Analysis',
                        action = function()
                            AIImageAnalyzer.clearAnalysis()
                        end,
                    },
                },
            },
        }
    end,
}
