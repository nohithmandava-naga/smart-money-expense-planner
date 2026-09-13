/* =========================================================
   SMART MONEY - SIDEBAR MENU
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const sideMenu = document.getElementById("sideMenu");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    const menuButton =
        document.querySelector(".menu-button");

    const closeButton =
        document.querySelector(".close-menu");

    const sidebarLinks =
        document.querySelectorAll(".sidebar-link");


    /* =====================================================
       OPEN MENU
    ===================================================== */

    function openMenu() {

        if (!sideMenu) {
            return;
        }

        sideMenu.classList.add("open");

        if (sidebarOverlay) {
            sidebarOverlay.classList.add("show");
        }

        document.body.style.overflow = "hidden";
    }


    /* =====================================================
       CLOSE MENU
    ===================================================== */

    function closeMenu() {

        if (!sideMenu) {
            return;
        }

        sideMenu.classList.remove("open");

        if (sidebarOverlay) {
            sidebarOverlay.classList.remove("show");
        }

        document.body.style.overflow = "";
    }


    /* =====================================================
       HAMBURGER BUTTON
    ===================================================== */

    if (menuButton) {

        menuButton.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                event.stopPropagation();

                openMenu();

            }
        );

    }


    /* =====================================================
       CLOSE BUTTON
    ===================================================== */

    if (closeButton) {

        closeButton.addEventListener(
            "click",
            function (event) {

                event.preventDefault();

                closeMenu();

            }
        );

    }


    /* =====================================================
       CLICK OVERLAY TO CLOSE
    ===================================================== */

    if (sidebarOverlay) {

        sidebarOverlay.addEventListener(
            "click",
            function () {

                closeMenu();

            }
        );

    }


    /* =====================================================
       SIDEBAR LINKS
    ===================================================== */

    sidebarLinks.forEach(function (link) {

        link.addEventListener(
            "click",
            function () {

                closeMenu();

            }
        );

    });


    /* =====================================================
       ESCAPE KEY
    ===================================================== */

    document.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Escape") {

                closeMenu();

            }

        }
    );


    /* =====================================================
       PREVENT SIDEBAR CLICK FROM CLOSING IT
    ===================================================== */

    if (sideMenu) {

        sideMenu.addEventListener(
            "click",
            function (event) {

                event.stopPropagation();

            }
        );

    }

});