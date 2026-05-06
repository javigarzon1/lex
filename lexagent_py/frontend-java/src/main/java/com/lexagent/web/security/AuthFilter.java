package com.lexagent.web.security;

import jakarta.servlet.*;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.stereotype.Component;

import java.io.IOException;

/** Redirige a /login si no hay sesión, salvo en rutas públicas. */
@Component
public class AuthFilter implements Filter {
    @Override
    public void doFilter(ServletRequest req, ServletResponse res, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest r = (HttpServletRequest) req;
        HttpServletResponse w = (HttpServletResponse) res;
        String path = r.getRequestURI();
        boolean isPublic = path.equals("/login") || path.equals("/signup")
                || path.startsWith("/css/") || path.startsWith("/js/")
                || path.startsWith("/static/") || path.equals("/favicon.ico");
        Object token = r.getSession().getAttribute("token");
        if (!isPublic && token == null) {
            w.sendRedirect("/login");
            return;
        }
        chain.doFilter(req, res);
    }
}
