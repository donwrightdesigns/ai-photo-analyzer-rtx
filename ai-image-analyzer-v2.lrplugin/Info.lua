return {
    LrSdkVersion = 13.0,
    LrSdkMinimumVersion = 6.0,
    
    LrToolkitIdentifier = 'com.aiimageanalyzer.desktop.lrplugin',
    LrPluginName = "AI Image Analyzer (Desktop)",
    VERSION = { display = "2.0" },
    
    -- Plugin description
    LrPluginInfoUrl = "https://github.com/ai-image-analyzer",
    
    -- Main menu items - Topaz-style simplicity
    LrLibraryMenuItems = {
        {
            title = "Send to AI Image Analyzer",
            file = "SendToAnalyzer.lua",
        },
        {
            title = "AI Image Analyzer - Archive Mode",
            file = "ArchiveMode.lua",
        },
        {
            title = "AI Image Analyzer - Curated Mode", 
            file = "CuratedMode.lua",
        },
        {
            title = "Refresh Metadata from IPTC",
            file = "RefreshMetadata.lua",
        },
    },
    
    -- Context menu for right-click
    LrPhotoMenuItems = {
        {
            title = "Send to AI Image Analyzer",
            file = "SendToAnalyzer.lua",
        },
    },
    
    -- Optional: Custom metadata fields for display
    LrMetadataProvider = "MetadataProvider.lua",
}
