package com.lexagent.web.controllers;

import java.util.Map;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;

import com.lexagent.web.client.LexAgentApiClient;

import jakarta.servlet.http.HttpSession;

@Controller
public class AuthController {

    private final LexAgentApiClient api;

    public AuthController(LexAgentApiClient api) { this.api = api; }

    @GetMapping("/login")
    public String loginPage() { return "login"; }

    @PostMapping("/login")
    public String login(@RequestParam String email, @RequestParam String password,
                        HttpSession session, RedirectAttributes ra, Model model) {
        try {
            Map<String, Object> r = api.login(email, password);
            session.setAttribute("token", r.get("token"));
            session.setAttribute("email", r.get("email"));
            return "redirect:/";
        } catch (HttpClientErrorException e) {
            model.addAttribute("error", api.extractApiError(e));
            model.addAttribute("email", email);
            return "login";
        }
    }

    @GetMapping("/signup")
    public String signupPage() { return "signup"; }

    @PostMapping("/signup")
    public String signup(@RequestParam String email, @RequestParam String password,
                         HttpSession session, Model model) {
        try {
            Map<String, Object> r = api.signup(email, password);
            session.setAttribute("token", r.get("token"));
            session.setAttribute("email", r.get("email"));
            return "redirect:/";
        } catch (HttpClientErrorException e) {
            model.addAttribute("error", api.extractApiError(e));
            model.addAttribute("email", email);
            return "signup";
        }
    }

    @PostMapping("/logout")
    public String logout(HttpSession session) {
        Object t = session.getAttribute("token");
        if (t != null) api.logout(String.valueOf(t));
        session.invalidate();
        return "redirect:/login";
    }
}
