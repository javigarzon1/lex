package com.lexagent.web.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.util.*;

@Component
public class LexAgentApiClient {

    private final RestTemplate rest;
    private final String baseUrl;
    private final ObjectMapper mapper = new ObjectMapper();

    public LexAgentApiClient(RestTemplate rest,
                             @Value("${lexagent.api.base-url}") String baseUrl) {
        this.rest = rest;
        this.baseUrl = baseUrl.replaceAll("/+$", "");
    }

    private HttpHeaders headers(String token) {
        HttpHeaders h = new HttpHeaders();
        h.setContentType(MediaType.APPLICATION_JSON);
        if (token != null && !token.isBlank()) h.setBearerAuth(token);
        return h;
    }

    public String extractApiError(HttpClientErrorException e) {
        try {
            Map<?, ?> m = mapper.readValue(e.getResponseBodyAsString(), Map.class);
            Object detail = m.get("detail");
            return detail != null ? String.valueOf(detail) : e.getStatusText();
        } catch (Exception ex) {
            return e.getStatusText();
        }
    }

    // ---------- Auth ----------
    @SuppressWarnings("unchecked")
    public Map<String, Object> login(String email, String password) {
        Map<String, Object> body = Map.of("email", email, "password", password);
        return rest.exchange(baseUrl + "/auth/login", HttpMethod.POST,
                new HttpEntity<>(body, headers(null)), Map.class).getBody();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> signup(String email, String password) {
        Map<String, Object> body = Map.of("email", email, "password", password);
        return rest.exchange(baseUrl + "/auth/signup", HttpMethod.POST,
                new HttpEntity<>(body, headers(null)), Map.class).getBody();
    }

    public void logout(String token) {
        try {
            rest.exchange(baseUrl + "/auth/logout", HttpMethod.POST,
                    new HttpEntity<>(null, headers(token)), Void.class);
        } catch (Exception ignored) { }
    }

    // ---------- Agents ----------
    @SuppressWarnings("unchecked")
    public Map<String, Object> listAgents(String token, String search, int page, int pageSize) {
        String url = baseUrl + "/agents?page=" + page + "&page_size=" + pageSize
                + "&search=" + java.net.URLEncoder.encode(search == null ? "" : search,
                java.nio.charset.StandardCharsets.UTF_8);
        return rest.exchange(url, HttpMethod.GET,
                new HttpEntity<>(headers(token)), Map.class).getBody();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getAgent(String token, String id) {
        return rest.exchange(baseUrl + "/agents/" + id, HttpMethod.GET,
                new HttpEntity<>(headers(token)), Map.class).getBody();
    }

    @SuppressWarnings("unchecked")
    public String createAgent(String token, Map<String, Object> payload) {
        Map<String, Object> r = rest.exchange(baseUrl + "/agents", HttpMethod.POST,
                new HttpEntity<>(payload, headers(token)), Map.class).getBody();
        return r != null ? String.valueOf(r.get("id")) : null;
    }

    public void updateAgent(String token, String id, Map<String, Object> payload) {
        rest.exchange(baseUrl + "/agents/" + id, HttpMethod.PUT,
                new HttpEntity<>(payload, headers(token)), Void.class);
    }

    public void deleteAgent(String token, String id) {
        rest.exchange(baseUrl + "/agents/" + id, HttpMethod.DELETE,
                new HttpEntity<>(headers(token)), Void.class);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> runAgent(String token, String id, Map<String, Object> formData) {
        return rest.exchange(baseUrl + "/agents/" + id + "/run", HttpMethod.POST,
                new HttpEntity<>(Map.of("form_data", formData), headers(token)),
                Map.class).getBody();
    }

    public byte[] export(String token, String markdown, String filename, String format) {
        Map<String, Object> body = Map.of("markdown", markdown,
                "filename", filename, "format", format);
        return rest.exchange(baseUrl + "/export", HttpMethod.POST,
                new HttpEntity<>(body, headers(token)), byte[].class).getBody();
    }

    @SuppressWarnings("unchecked")
    public String extractKnowledge(String token, byte[] content, String filename) {
        HttpHeaders h = new HttpHeaders();
        h.setContentType(MediaType.MULTIPART_FORM_DATA);
        if (token != null) h.setBearerAuth(token);
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new ByteArrayResource(content) {
            @Override public String getFilename() { return filename; }
        });
        Map<String, Object> r = rest.exchange(baseUrl + "/knowledge/extract", HttpMethod.POST,
                new HttpEntity<>(body, h), Map.class).getBody();
        return r != null ? String.valueOf(r.get("text")) : "";
    }
}
