// On neutralise la géolocalisation pour éviter les erreurs de blocage Tor/Browser
(function() {
    const mockGeolocation = {
        getCurrentPosition: function(success, error, options) {
            console.log("Web No Geolocation: Simulation d'une position vide pour compatibilité.");
            if (success) {
                success({
                    coords: {
                        latitude: 0.0,
                        longitude: 0.0,
                        accuracy: 0
                    },
                    timestamp: Date.now()
                });
            }
        },
        watchPosition: function(success, error, options) {
            return 1; // Dummy ID
        },
        clearWatch: function(id) {}
    };

    if (typeof navigator !== 'undefined' && !navigator.geolocation) {
        try {
            Object.defineProperty(navigator, 'geolocation', {
                value: mockGeolocation,
                configurable: true,
                enumerable: true,
                writable: true
            });
        } catch (e) {
            console.warn("Web No Geolocation: Impossible de définir navigator.geolocation directement.", e);
            try {
                navigator.geolocation = mockGeolocation;
            } catch (e2) {
                console.error("Web No Geolocation: Échec total de l'injection.", e2);
            }
        }
    } else if (typeof navigator !== 'undefined' && navigator.geolocation) {
        // Si elle existe mais qu'on veut quand même la neutraliser (ex: HTTPS mais Tor)
        navigator.geolocation.getCurrentPosition = mockGeolocation.getCurrentPosition;
        navigator.geolocation.watchPosition = mockGeolocation.watchPosition;
    }
})();
