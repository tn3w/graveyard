console.log(
    (function () {
        try {
            Object.setPrototypeOf(Math.sin, Math.sin);
            return 'no error';
        } catch (e) {
            return e.message;
        }
    })()
);
