-- Simple JSON parser for Lightroom
-- Based on the JSON4Lua library

local JSON = {}

local function decode_scanWhitespace(s, startPos)
    local whitespace = " \t\r\n"
    local stringLen = string.len(s)
    while (stringLen >= startPos and string.find(whitespace, string.sub(s, startPos, startPos))) do
        startPos = startPos + 1   
    end
    return startPos
end

local function decode_scanString(s, startPos)
    assert(string.sub(s, startPos, startPos) == '"', 'decode_scanString must start with "')
    local stringEnd = startPos + 1
    local stringLen = string.len(s)
    while (stringEnd <= stringLen and string.sub(s, stringEnd, stringEnd) ~= '"') do
        local char = string.sub(s, stringEnd, stringEnd)
        if char == '\\' then
            stringEnd = stringEnd + 1
        end
        stringEnd = stringEnd + 1
    end
    assert(stringEnd <= stringLen, "Unterminated string")
    local stringValue = string.sub(s, startPos + 1, stringEnd - 1)
    return stringValue, stringEnd + 1
end

local function decode_scanNumber(s, startPos)
    local numberEnd = startPos
    local stringLen = string.len(s)
    local acceptableChars = "+-0123456789.e"
    while (numberEnd <= stringLen and string.find(acceptableChars, string.sub(s, numberEnd, numberEnd))) do
        numberEnd = numberEnd + 1
    end
    local numberString = string.sub(s, startPos, numberEnd - 1)
    return tonumber(numberString), numberEnd
end

local function decode_scanConstant(s, startPos)
    local constantNames = {["true"] = true, ["false"] = false, ["null"] = nil}
    local stringLen = string.len(s)
    for constant, value in pairs(constantNames) do
        local constantEnd = startPos + string.len(constant) - 1
        if constantEnd <= stringLen then
            local constantString = string.sub(s, startPos, constantEnd)
            if constantString == constant then
                return value, constantEnd + 1
            end
        end
    end
    assert(nil, "Failed to scan constant from string " .. s .. " at " .. startPos)
end

local function decode_scanValue(s, startPos)
    startPos = decode_scanWhitespace(s, startPos)
    local curChar = string.sub(s, startPos, startPos)
    
    if curChar == '"' then
        return decode_scanString(s, startPos)
    elseif string.find("+-0123456789", curChar) then
        return decode_scanNumber(s, startPos)
    elseif curChar == '{' then
        return decode_scanObject(s, startPos)
    elseif curChar == '[' then
        return decode_scanArray(s, startPos)
    elseif string.find("tfn", curChar) then
        return decode_scanConstant(s, startPos)
    else
        assert(nil, "Failed to scan value at " .. startPos .. " '" .. curChar .. "'")
    end
end

local function decode_scanObject(s, startPos)
    local object = {}
    assert(string.sub(s, startPos, startPos) == '{', "decode_scanObject must start with '{'")
    startPos = startPos + 1
    startPos = decode_scanWhitespace(s, startPos)
    
    if string.sub(s, startPos, startPos) == '}' then
        return object, startPos + 1
    end
    
    while true do
        local key, keyEndPos = decode_scanValue(s, startPos)
        assert(type(key) == "string", "Object key must be a string")
        
        startPos = decode_scanWhitespace(s, keyEndPos)
        assert(string.sub(s, startPos, startPos) == ':', "Object key must be followed by ':'")
        startPos = startPos + 1
        
        local value, valueEndPos = decode_scanValue(s, startPos)
        object[key] = value
        startPos = decode_scanWhitespace(s, valueEndPos)
        
        local curChar = string.sub(s, startPos, startPos)
        if curChar == '}' then
            return object, startPos + 1
        elseif curChar == ',' then
            startPos = startPos + 1
        else
            assert(nil, "Object must end with '}' or continue with ','")
        end
        
        startPos = decode_scanWhitespace(s, startPos)
    end
end

local function decode_scanArray(s, startPos)
    local array = {}
    assert(string.sub(s, startPos, startPos) == '[', "decode_scanArray must start with '['")
    startPos = startPos + 1
    startPos = decode_scanWhitespace(s, startPos)
    
    if string.sub(s, startPos, startPos) == ']' then
        return array, startPos + 1
    end
    
    local arrayIndex = 1
    while true do
        local value, valueEndPos = decode_scanValue(s, startPos)
        array[arrayIndex] = value
        arrayIndex = arrayIndex + 1
        startPos = decode_scanWhitespace(s, valueEndPos)
        
        local curChar = string.sub(s, startPos, startPos)
        if curChar == ']' then
            return array, startPos + 1
        elseif curChar == ',' then
            startPos = startPos + 1
        else
            assert(nil, "Array must end with ']' or continue with ','")
        end
        
        startPos = decode_scanWhitespace(s, startPos)
    end
end

function JSON:decode(s)
    if s == nil then
        return nil
    end
    
    local object, endPos = decode_scanValue(s, 1)
    return object
end

function JSON:encode(object)
    if object == nil then
        return "null"
    elseif type(object) == "string" then
        return '"' .. string.gsub(object, '"', '\\"') .. '"'
    elseif type(object) == "number" then
        return tostring(object)
    elseif type(object) == "boolean" then
        return object and "true" or "false"
    elseif type(object) == "table" then
        -- Check if it's an array
        local isArray = true
        local length = 0
        for k, v in pairs(object) do
            length = length + 1
            if type(k) ~= "number" or k ~= length then
                isArray = false
                break
            end
        end
        
        if isArray then
            local result = "["
            for i = 1, length do
                if i > 1 then result = result .. "," end
                result = result .. JSON:encode(object[i])
            end
            return result .. "]"
        else
            local result = "{"
            local first = true
            for k, v in pairs(object) do
                if not first then result = result .. "," end
                result = result .. JSON:encode(tostring(k)) .. ":" .. JSON:encode(v)
                first = false
            end
            return result .. "}"
        end
    end
    
    return "null"
end

return JSON
