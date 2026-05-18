package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
)

type APIClient struct {
	baseURL   *url.URL
	client    *http.Client
	sessionID string
}

type HTTPResult struct {
	StatusCode int
	Body       []byte
}

func NewAPIClient(baseURL string, sessionID string) (*APIClient, error) {
	parsed, err := url.Parse(strings.TrimRight(baseURL, "/"))
	if err != nil {
		return nil, fmt.Errorf("invalid AIOGRAPI_REST_BASE_URL: %w", err)
	}
	if parsed.Scheme == "" || parsed.Host == "" {
		return nil, fmt.Errorf("invalid AIOGRAPI_REST_BASE_URL: %q", baseURL)
	}

	return &APIClient{
		baseURL:   parsed,
		client:    http.DefaultClient,
		sessionID: sessionID,
	}, nil
}

func (c *APIClient) Get(path string, query url.Values) (*HTTPResult, error) {
	return c.request(http.MethodGet, path, query, nil, "")
}

func (c *APIClient) PostForm(path string, form url.Values) (*HTTPResult, error) {
	return c.request(
		http.MethodPost,
		path,
		nil,
		strings.NewReader(form.Encode()),
		"application/x-www-form-urlencoded",
	)
}

func (c *APIClient) request(method string, path string, query url.Values, body io.Reader, contentType string) (*HTTPResult, error) {
	endpoint := c.baseURL.ResolveReference(&url.URL{Path: "/" + strings.TrimLeft(path, "/")})
	if query != nil {
		endpoint.RawQuery = query.Encode()
	}

	req, err := http.NewRequest(method, endpoint.String(), body)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Accept", "application/json")
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}
	if c.sessionID != "" {
		req.Header.Set("X-Session-ID", c.sessionID)
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	return &HTTPResult{StatusCode: resp.StatusCode, Body: data}, nil
}

func env(name string) string {
	return strings.TrimSpace(os.Getenv(name))
}

func envDefault(name string, fallback string) string {
	if value := env(name); value != "" {
		return value
	}
	return fallback
}

func printResult(title string, result *HTTPResult) {
	fmt.Printf("\n%s [HTTP %d]\n%s\n", title, result.StatusCode, prettyJSON(result.Body))
}

func prettyJSON(data []byte) string {
	var value any
	if err := json.Unmarshal(data, &value); err != nil {
		return string(data)
	}

	rendered, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		return string(data)
	}
	return string(bytes.TrimSpace(rendered))
}

func decodeLogin(body []byte) (string, error) {
	var value string
	if err := json.Unmarshal(body, &value); err != nil {
		return "", err
	}
	if value == "" || value == "false" {
		return "", errors.New("login did not return a usable session")
	}
	return value, nil
}

func main() {
	api, err := NewAPIClient(
		envDefault("AIOGRAPI_REST_BASE_URL", "http://localhost:8000"),
		env("AIOGRAPI_REST_SESSIONID"),
	)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}

	health, err := api.Get("/health", nil)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	printResult("Health", health)

	deps, err := api.Get("/deps", nil)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	printResult("Dependencies", deps)

	if api.sessionID == "" && env("AIOGRAPI_REST_USERNAME") != "" && env("AIOGRAPI_REST_PASSWORD") != "" {
		form := url.Values{}
		form.Set("username", env("AIOGRAPI_REST_USERNAME"))
		form.Set("password", env("AIOGRAPI_REST_PASSWORD"))
		if verificationCode := env("AIOGRAPI_REST_VERIFICATION_CODE"); verificationCode != "" {
			form.Set("verification_code", verificationCode)
		}

		login, err := api.PostForm("/auth/login", form)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
		printResult("Login", login)
		if login.StatusCode >= 200 && login.StatusCode < 300 {
			api.sessionID, err = decodeLogin(login.Body)
			if err != nil {
				fmt.Fprintln(os.Stderr, err)
				os.Exit(1)
			}
			fmt.Println("\nLogin stored the returned session for this process.")
		}
	}

	if api.sessionID == "" {
		fmt.Println("\nSet AIOGRAPI_REST_SESSIONID or AIOGRAPI_REST_USERNAME/AIOGRAPI_REST_PASSWORD to call /user/about.")
		return
	}

	query := url.Values{}
	query.Set("user_id", envDefault("AIOGRAPI_REST_USER_ID", "25025320"))
	about, err := api.Get("/user/about", query)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	printResult("User About", about)
}
