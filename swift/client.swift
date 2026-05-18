#!/usr/bin/env swift

import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

struct HTTPResult {
    let statusCode: Int
    let body: String
}

enum ClientError: Error, CustomStringConvertible {
    case invalidBaseURL(String)
    case invalidURL(String)
    case requestFailed(Error)
    case missingHTTPResponse

    var description: String {
        switch self {
        case .invalidBaseURL(let value):
            return "Invalid AIOGRAPI_REST_BASE_URL: \(value)"
        case .invalidURL(let value):
            return "Invalid URL: \(value)"
        case .requestFailed(let error):
            return "Request failed: \(error)"
        case .missingHTTPResponse:
            return "Missing HTTP response"
        }
    }
}

final class APIClient {
    private let baseURL: URL
    var sessionID: String?

    init(baseURL: String, sessionID: String?) throws {
        guard let url = URL(string: baseURL) else {
            throw ClientError.invalidBaseURL(baseURL)
        }
        self.baseURL = url
        self.sessionID = sessionID
    }

    func get(_ path: String, queryItems: [URLQueryItem] = []) throws -> HTTPResult {
        try request("GET", path: path, queryItems: queryItems)
    }

    func postForm(_ path: String, fields: [String: String]) throws -> HTTPResult {
        try request(
            "POST",
            path: path,
            body: formBody(fields),
            contentType: "application/x-www-form-urlencoded"
        )
    }

    func login(username: String, password: String, verificationCode: String?) throws -> HTTPResult {
        var fields = [
            "username": username,
            "password": password,
        ]
        if let verificationCode {
            fields["verification_code"] = verificationCode
        }
        return try postForm("/auth/login", fields: fields)
    }

    func importInstagramSessionID(_ instagramSessionID: String) throws -> HTTPResult {
        try postForm("/auth/login/by/sessionid", fields: ["sessionid": instagramSessionID])
    }

    private func request(
        _ method: String,
        path: String,
        queryItems: [URLQueryItem] = [],
        body: Data? = nil,
        contentType: String? = nil
    ) throws -> HTTPResult {
        let cleanPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        var url = baseURL.appendingPathComponent(cleanPath)

        if !queryItems.isEmpty {
            guard var components = URLComponents(url: url, resolvingAgainstBaseURL: false) else {
                throw ClientError.invalidURL(url.absoluteString)
            }
            components.queryItems = queryItems
            guard let composedURL = components.url else {
                throw ClientError.invalidURL(url.absoluteString)
            }
            url = composedURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let sessionID {
            request.setValue(sessionID, forHTTPHeaderField: "X-Session-ID")
        }
        if let contentType {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        request.httpBody = body

        let semaphore = DispatchSemaphore(value: 0)
        var responseData: Data?
        var response: URLResponse?
        var responseError: Error?

        URLSession.shared.dataTask(with: request) { data, urlResponse, error in
            responseData = data
            response = urlResponse
            responseError = error
            semaphore.signal()
        }.resume()

        semaphore.wait()

        if let responseError {
            throw ClientError.requestFailed(responseError)
        }
        guard let httpResponse = response as? HTTPURLResponse else {
            throw ClientError.missingHTTPResponse
        }

        return HTTPResult(
            statusCode: httpResponse.statusCode,
            body: responseData.flatMap { String(data: $0, encoding: .utf8) } ?? ""
        )
    }
}

func formBody(_ fields: [String: String]) -> Data {
    var components = URLComponents()
    components.queryItems = fields.map { URLQueryItem(name: $0.key, value: $0.value) }
    return Data((components.percentEncodedQuery ?? "").utf8)
}

func env(_ name: String) -> String? {
    let value = ProcessInfo.processInfo.environment[name]?.trimmingCharacters(in: .whitespacesAndNewlines)
    return value?.isEmpty == false ? value : nil
}

func prettyBody(_ body: String) -> String {
    guard let data = body.data(using: .utf8),
          let json = try? JSONSerialization.jsonObject(with: data),
          JSONSerialization.isValidJSONObject(json),
          let pretty = try? JSONSerialization.data(withJSONObject: json, options: [.prettyPrinted, .sortedKeys]),
          let rendered = String(data: pretty, encoding: .utf8) else {
        return body
    }
    return rendered
}

func printResult(_ title: String, _ result: HTTPResult) {
    print("\n\(title) [HTTP \(result.statusCode)]")
    print(prettyBody(result.body))
}

func sessionID(from body: String) -> String? {
    guard let data = body.data(using: .utf8),
          let value = try? JSONDecoder().decode(String.self, from: data),
          !value.isEmpty,
          value != "false" else {
        return nil
    }
    return value
}

do {
    let client = try APIClient(
        baseURL: env("AIOGRAPI_REST_BASE_URL") ?? "http://localhost:8000",
        sessionID: env("AIOGRAPI_REST_SESSIONID")
    )

    printResult("Health", try client.get("/health"))
    printResult("Dependencies", try client.get("/deps"))

    if client.sessionID == nil,
       let instagramSessionID = env("AIOGRAPI_REST_INSTAGRAM_SESSIONID") {
        let login = try client.importInstagramSessionID(instagramSessionID)
        printResult("Import Session", login)
        client.sessionID = sessionID(from: login.body)
        if client.sessionID != nil {
            print("\nImported session stored for this process.")
        }
    }

    if client.sessionID == nil,
       let username = env("AIOGRAPI_REST_USERNAME"),
       let password = env("AIOGRAPI_REST_PASSWORD") {
        let login = try client.login(
            username: username,
            password: password,
            verificationCode: env("AIOGRAPI_REST_VERIFICATION_CODE")
        )
        printResult("Login", login)
        client.sessionID = sessionID(from: login.body)
        if client.sessionID != nil {
            print("\nLogin stored the returned session for this process.")
        }
    }

    if client.sessionID != nil {
        let userID = env("AIOGRAPI_REST_USER_ID") ?? "25025320"
        printResult(
            "User About",
            try client.get("/user/about", queryItems: [URLQueryItem(name: "user_id", value: userID)])
        )
    } else {
        print(
            "\nSet AIOGRAPI_REST_SESSIONID, AIOGRAPI_REST_INSTAGRAM_SESSIONID, " +
            "or AIOGRAPI_REST_USERNAME/AIOGRAPI_REST_PASSWORD to call /user/about."
        )
    }
} catch {
    fputs("\(error)\n", stderr)
    exit(1)
}
