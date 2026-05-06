package com.lexagent.web;

import com.lexagent.web.security.AuthFilter;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestTemplate;

@SpringBootApplication
public class LexAgentApplication {
    public static void main(String[] args) {
        SpringApplication.run(LexAgentApplication.class, args);
    }

    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }

    @Bean
    public FilterRegistrationBean<AuthFilter> authFilter(AuthFilter f) {
        FilterRegistrationBean<AuthFilter> r = new FilterRegistrationBean<>(f);
        r.addUrlPatterns("/*");
        r.setOrder(1);
        return r;
    }
}
