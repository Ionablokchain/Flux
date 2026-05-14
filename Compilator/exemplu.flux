intentie Main {
    declansare: la_primul_semn_cognitiv()
    prioritate: 0.9
    conditie: vid_cauzal.exista()
    executa: {
        trimite_senzatie("imagine mentală", "╔════════════════════╗\n║   Bun venit în    ║\n║    Ex Nihilo!     ║\n╚════════════════════╝", 2s);
        
        raspuns = asculta_intentie(utilizator, 10s, "tăcere");
        
        daca raspuns != "tăcere" : {
            colapseaza(raspuns, "pondere_maximă");
            trimite_senzatie("vorbire interioară", "Ai spus: " ++ raspuns, 1s);
        } altfel : {
            trimite_senzatie("senzație tactilă", "Niciun răspuns. Se creează un paradox educațional.", 0.5s);
        }
        
        retur;
    }
}