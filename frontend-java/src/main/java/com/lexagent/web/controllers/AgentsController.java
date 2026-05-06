package com.lexagent.web.controllers;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.lexagent.web.client.LexAgentApiClient;
import jakarta.servlet.http.HttpSession;
import org.commonmark.parser.Parser;
import org.commonmark.renderer.html.HtmlRenderer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import java.util.*;

@Controller
public class AgentsController {

    private final LexAgentApiClient api;
    private final Parser mdParser = Parser.builder().build();
    private final HtmlRenderer mdRenderer = HtmlRenderer.builder().build();
    private final ObjectMapper mapper = new ObjectMapper();

    public AgentsController(LexAgentApiClient api) { this.api = api; }

    private String token(HttpSession s) { return (String) s.getAttribute("token"); }

    private String md(String m) {
        if (m == null) return "";
        return mdRenderer.render(mdParser.parse(m));
    }

    @GetMapping("/")
    public String index(@RequestParam(defaultValue = "") String q,
                        @RequestParam(defaultValue = "1") int page,
                        HttpSession session, Model model) {
        int pageSize = 10;
        Map<String, Object> r = api.listAgents(token(session), q, page, pageSize);
        long total = r.get("total") instanceof Number n ? n.longValue() : 0L;
        model.addAttribute("agents", r.get("items"));
        model.addAttribute("q", q);
        model.addAttribute("page", page);
        model.addAttribute("pageSize", pageSize);
        model.addAttribute("total", total);
        model.addAttribute("totalPages", Math.max(1, (int) Math.ceil(total / (double) pageSize)));
        model.addAttribute("email", session.getAttribute("email"));
        return "index";
    }

    @GetMapping("/agents/new")
    public String newAgent(Model model) {
        model.addAttribute("mode", "new");
        return "new-agent";
    }

    @GetMapping("/agents/{id}/edit")
    public String editAgent(@PathVariable String id, HttpSession session, Model model) {
        Map<String, Object> a = api.getAgent(token(session), id);
        model.addAttribute("agent", a);
        try {
            model.addAttribute("fieldsJson",
                    mapper.writeValueAsString(a.getOrDefault("form_fields", List.of())));
        } catch (Exception e) {
            model.addAttribute("fieldsJson", "[]");
        }
        model.addAttribute("mode", "edit");
        return "new-agent";
    }

    @PostMapping("/agents/new")
    public String createAgent(@RequestParam String name,
                              @RequestParam(required = false, defaultValue = "") String description,
                              @RequestParam String docType,
                              @RequestParam String systemPrompt,
                              @RequestParam(required = false, defaultValue = "") String knowledgeBase,
                              @RequestParam(required = false) MultipartFile knowledgeFile,
                              @RequestParam(required = false) String fieldsJson,
                              HttpSession session, RedirectAttributes ra) throws Exception {
        Map<String, Object> payload = buildPayload(token(session), name, description,
                docType, systemPrompt, knowledgeBase, knowledgeFile, fieldsJson);
        String id = api.createAgent(token(session), payload);
        ra.addFlashAttribute("flash", "Agente creado correctamente.");
        return "redirect:/agents/" + id;
    }

    @PostMapping("/agents/{id}/edit")
    public String updateAgent(@PathVariable String id,
                              @RequestParam String name,
                              @RequestParam(required = false, defaultValue = "") String description,
                              @RequestParam String docType,
                              @RequestParam String systemPrompt,
                              @RequestParam(required = false, defaultValue = "") String knowledgeBase,
                              @RequestParam(required = false) MultipartFile knowledgeFile,
                              @RequestParam(required = false) String fieldsJson,
                              HttpSession session, RedirectAttributes ra) throws Exception {
        Map<String, Object> payload = buildPayload(token(session), name, description,
                docType, systemPrompt, knowledgeBase, knowledgeFile, fieldsJson);
        api.updateAgent(token(session), id, payload);
        ra.addFlashAttribute("flash", "Cambios guardados.");
        return "redirect:/agents/" + id;
    }

    private Map<String, Object> buildPayload(String token, String name, String description,
                                             String docType, String systemPrompt,
                                             String knowledgeBase, MultipartFile knowledgeFile,
                                             String fieldsJson) throws Exception {
        String kb = knowledgeBase == null ? "" : knowledgeBase;
        if (knowledgeFile != null && !knowledgeFile.isEmpty()) {
            String extracted = api.extractKnowledge(token, knowledgeFile.getBytes(),
                    knowledgeFile.getOriginalFilename());
            kb = kb.isBlank() ? extracted : kb + "\n\n" + extracted;
        }
        List<Map<String, Object>> fields = parseFields(fieldsJson);
        Map<String, Object> payload = new HashMap<>();
        payload.put("name", name);
        payload.put("description", description);
        payload.put("doc_type", docType);
        payload.put("system_prompt", systemPrompt);
        payload.put("knowledge_base", kb);
        payload.put("form_fields", fields);
        return payload;
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> parseFields(String json) {
        if (json == null || json.isBlank()) return List.of();
        try { return mapper.readValue(json, List.class); }
        catch (Exception e) { return List.of(); }
    }

    @GetMapping("/agents/{id}")
    public String agent(@PathVariable String id, HttpSession session, Model model) {
        Map<String, Object> a = api.getAgent(token(session), id);
        model.addAttribute("agent", a);
        return "agent";
    }

    @PostMapping("/agents/{id}/delete")
    public String delete(@PathVariable String id, HttpSession session, RedirectAttributes ra) {
        api.deleteAgent(token(session), id);
        ra.addFlashAttribute("flash", "Agente eliminado.");
        return "redirect:/";
    }

    @PostMapping("/agents/{id}/run")
    public String run(@PathVariable String id,
                      @RequestParam Map<String, String> allParams,
                      HttpSession session, Model model) {
        Map<String, Object> a = api.getAgent(token(session), id);
        Map<String, Object> formData = new LinkedHashMap<>();
        for (Map.Entry<String, String> e : allParams.entrySet()) {
            if (e.getKey().startsWith("f_")) {
                formData.put(e.getKey().substring(2), e.getValue());
            }
        }
        Map<String, Object> result = api.runAgent(token(session), id, formData);
        model.addAttribute("agent", a);
        model.addAttribute("formData", formData);
        model.addAttribute("reportMd", result.get("report"));
        model.addAttribute("documentMd", result.get("document"));
        model.addAttribute("reportHtml", md((String) result.get("report")));
        model.addAttribute("documentHtml", md((String) result.get("document")));
        return "result";
    }

    @PostMapping("/export")
    public ResponseEntity<byte[]> export(@RequestParam String markdown,
                                         @RequestParam(defaultValue = "documento") String filename,
                                         @RequestParam(defaultValue = "pdf") String format,
                                         HttpSession session) {
        byte[] data = api.export(token(session), markdown, filename, format);
        MediaType mt = "pdf".equals(format) ? MediaType.APPLICATION_PDF
                : MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        return ResponseEntity.ok()
                .contentType(mt)
                .header(HttpHeaders.CONTENT_DISPOSITION,
                        "attachment; filename=\"" + filename + "." + format + "\"")
                .body(data);
    }
}
