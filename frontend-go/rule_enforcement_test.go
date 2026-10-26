package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"testing"
)

func TestConfigureRulesUsesSharedBackendState(t *testing.T) {
	var payload ruleState
	f := frontend{activeLayout: "previous"}
	f.client = &http.Client{Transport: ruleTransport(func(r *http.Request) (*http.Response, error) {
		if r.Method != http.MethodPut || r.URL.Path != "/screenassign/rule-enforcement" {
			return nil, fmt.Errorf("unexpected endpoint: %s %s", r.Method, r.URL.Path)
		}
		if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
			t.Fatal(err)
		}
		return ruleResponse(`{"layout_name":"work","assignment":{"1":"monitor"},"configured":true}`, 200), nil
	})}
	if err := f.configureRules("work", map[string]string{"1": "monitor"}); err != nil {
		t.Fatal(err)
	}
	if f.activeLayout != "work" || payload.Layout != "work" || payload.Assignment["1"] != "monitor" {
		t.Fatal("configuration not mirrored")
	}
}

func TestConfigureRulesFailurePreservesUIState(t *testing.T) {
	f := frontend{activeLayout: "previous"}
	f.client = &http.Client{Transport: ruleTransport(func(r *http.Request) (*http.Response, error) {
		return ruleResponse(`{"error":"invalid assignment"}`, 409), nil
	})}
	if err := f.configureRules("invalid", map[string]string{}); err == nil {
		t.Fatal("expected validation error")
	}
	if f.activeLayout != "previous" {
		t.Fatal("failed activation replaced working layout")
	}
}

func TestStartupDoesNotOverrideSharedDeactivation(t *testing.T) {
	f := frontend{}
	count := 0
	f.client = &http.Client{Transport: ruleTransport(func(r *http.Request) (*http.Response, error) {
		count++
		if r.Method != http.MethodGet || r.URL.Path != "/screenassign/rule-enforcement" {
			t.Fatalf("unexpected startup request: %s %s", r.Method, r.URL.Path)
		}
		return ruleResponse(`{"layout_name":null,"assignment":{},"configured":true}`, 200), nil
	})}
	f.initializeRuleState()
	if count != 1 || f.activeLayout != "" {
		t.Fatal("startup must preserve shared deactivation")
	}
}
