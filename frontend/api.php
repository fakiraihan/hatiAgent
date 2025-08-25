<?php
/**
 * PHP Bridge untuk Hati Backend API
 * Provides secure proxy to Python FastAPI backend
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

// Handle preflight requests
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(200);
    exit();
}

// Configuration
$BACKEND_URL = getenv('HATI_BACKEND_URL') ?: 'http://localhost:8000';
$API_TIMEOUT = 30; // seconds

/**
 * Make HTTP request to backend API
 */
function makeApiRequest($endpoint, $method = 'GET', $data = null) {
    global $BACKEND_URL, $API_TIMEOUT;
    
    $url = $BACKEND_URL . $endpoint;
    
    $options = [
        'http' => [
            'method' => $method,
            'timeout' => $API_TIMEOUT,
            'header' => [
                'Content-Type: application/json',
                'User-Agent: Hati-PHP-Bridge/1.0'
            ]
        ]
    ];
    
    if ($data && in_array($method, ['POST', 'PUT', 'PATCH'])) {
        $options['http']['content'] = json_encode($data);
    }
    
    $context = stream_context_create($options);
    $response = @file_get_contents($url, false, $context);
    
    if ($response === false) {
        return [
            'error' => true,
            'message' => 'Failed to connect to backend service',
            'code' => 'CONNECTION_ERROR'
        ];
    }
    
    $httpCode = 200;
    if (isset($http_response_header[0])) {
        preg_match('/HTTP\/\d\.\d\s+(\d+)/', $http_response_header[0], $matches);
        if (isset($matches[1])) {
            $httpCode = intval($matches[1]);
        }
    }
    
    $decodedResponse = json_decode($response, true);
    
    return [
        'error' => $httpCode >= 400,
        'http_code' => $httpCode,
        'data' => $decodedResponse ?: $response
    ];
}

/**
 * Route handler
 */
$requestUri = $_SERVER['REQUEST_URI'];
$requestMethod = $_SERVER['REQUEST_METHOD'];

// Parse the request path
$path = parse_url($requestUri, PHP_URL_PATH);
$pathParts = explode('/', trim($path, '/'));

// Remove 'api.php' from path if present
if ($pathParts[0] === 'api.php') {
    array_shift($pathParts);
}

$route = '/' . implode('/', $pathParts);

// Handle different routes
switch ($route) {
    case '/health':
        $result = makeApiRequest('/health');
        break;
        
    case '/chat':
        if ($requestMethod !== 'POST') {
            http_response_code(405);
            echo json_encode(['error' => 'Method not allowed']);
            exit();
        }
        
        $input = file_get_contents('php://input');
        $data = json_decode($input, true);
        
        if (!$data || !isset($data['message'])) {
            http_response_code(400);
            echo json_encode(['error' => 'Invalid request body']);
            exit();
        }
        
        // Add some basic validation and sanitization
        $message = trim($data['message']);
        if (empty($message)) {
            http_response_code(400);
            echo json_encode(['error' => 'Message cannot be empty']);
            exit();
        }
        
        if (strlen($message) > 2000) {
            http_response_code(400);
            echo json_encode(['error' => 'Message too long (max 2000 characters)']);
            exit();
        }
        
        // Forward to enhanced backend endpoint
        $result = makeApiRequest('/chat-enhanced', 'POST', $data);
        break;
        
    case '/chat-enhanced':
        if ($requestMethod !== 'POST') {
            http_response_code(405);
            echo json_encode(['error' => 'Method not allowed']);
            exit();
        }
        
        $input = file_get_contents('php://input');
        $data = json_decode($input, true);
        
        if (!$data || !isset($data['message'])) {
            http_response_code(400);
            echo json_encode(['error' => 'Invalid request body']);
            exit();
        }
        
        // Add some basic validation and sanitization
        $message = trim($data['message']);
        if (empty($message)) {
            http_response_code(400);
            echo json_encode(['error' => 'Message cannot be empty']);
            exit();
        }
        
        if (strlen($message) > 2000) {
            http_response_code(400);
            echo json_encode(['error' => 'Message too long (max 2000 characters)']);
            exit();
        }
        
        // Forward to enhanced backend endpoint
        $result = makeApiRequest('/chat-enhanced', 'POST', $data);
        break;
        
    case '/music/tracks':
        $result = makeApiRequest('/music/tracks');
        break;
        
    default:
        http_response_code(404);
        echo json_encode(['error' => 'Endpoint not found']);
        exit();
}

// Return response
if ($result['error']) {
    http_response_code($result['http_code'] ?? 500);
    echo json_encode([
        'error' => true,
        'message' => $result['data']['detail'] ?? $result['message'] ?? 'Unknown error',
        'code' => $result['code'] ?? 'API_ERROR'
    ]);
} else {
    echo json_encode($result['data']);
}
?>
